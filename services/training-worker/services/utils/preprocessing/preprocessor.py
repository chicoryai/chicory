import itertools
import os
import json
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import hashlib
import threading
import queue
import fcntl
import uuid

from services.utils.logger import logger

# Third-party imports
try:
    from unstructured.partition.auto import partition
    from unstructured.staging.base import convert_to_dict

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logger.warning("unstructured package not available. Install with: pip install unstructured")

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import chardet

    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    logger.warning("chardet package not available for encoding detection. Install with: pip install chardet")

# LangChain text splitters
try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        CharacterTextSplitter,
        PythonCodeTextSplitter,
        MarkdownTextSplitter,
        HTMLHeaderTextSplitter,  # Use HTMLHeaderTextSplitter instead of HTMLTextSplitter
        CSVTextSplitter  # Add CSV text splitter
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("langchain_text_splitters package not available. Install with: pip install langchain-text-splitters")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available. Memory monitoring disabled.")


@dataclass
class ProcessingConfig:
    """Configuration for file processing"""
    max_file_size_mb: float = 1.0
    chunk_overlap: int = 100  # characters to overlap between chunks
    preserve_structure: bool = True
    delete_original: bool = False  # Flag to delete original file after splitting
    supported_formats: List[str] = None
    max_total_size_gb: float = 10.0  # Maximum total size to process in a single run
    max_files_per_run: int = 1000  # Maximum number of files to process

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = [
                # Text formats
                '.txt', '.md', '.rst', '.csv', '.json', '.xml', '.yaml', '.yml',
                # Document formats
                '.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
                # Code formats
                '.py', '.js', '.html', '.css', '.sql', '.java', '.cpp', '.c',
                # Image formats
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
                # Other formats
                '.log', '.ini', '.cfg', '.conf'
            ]


class FileChunker:
    """Handles chunking of different file types using LangChain text splitters"""

    @staticmethod
    def safe_byte_size(text: str) -> int:
        """Calculate actual byte size of text, handling Unicode properly"""
        if not text:
            return 0
        try:
            return len(text.encode('utf-8'))
        except (UnicodeError, AttributeError):
            # Fallback for edge cases
            return len(str(text).encode('utf-8', errors='replace'))

    @staticmethod
    def estimate_char_size_from_bytes(max_bytes: int, content_sample: str = None) -> int:
        """
        Dynamically estimate character count from byte limit using actual content sampling.
        Much more accurate than fixed ratios.
        """
        if max_bytes <= 0:
            return 1

        # If we have a content sample, use it to calculate actual bytes-per-char ratio
        if content_sample and len(content_sample) > 100:
            sample_chars = min(1000, len(content_sample))  # Use up to 1000 chars for sampling
            sample_text = content_sample[:sample_chars]
            sample_bytes = len(sample_text.encode('utf-8'))
            bytes_per_char = sample_bytes / sample_chars

            # Add 20% safety margin for encoding variation
            safe_chars = int(max_bytes / (bytes_per_char * 1.2))
            return max(1, safe_chars)

        # Fallback: Conservative estimate for unknown content
        # Assume worst case of 3 bytes per char (covers most UTF-8 content safely)
        estimated_chars = max_bytes // 3
        return max(1, estimated_chars)

    @staticmethod
    def get_appropriate_splitter(file_extension: str, max_size_bytes: int, overlap: int = 100, content_sample: str = None):
        """Get the appropriate LangChain text splitter based on file type"""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain text splitters not available")

        # Use dynamic estimation with content sampling when available
        chunk_size = FileChunker.estimate_char_size_from_bytes(max_size_bytes, content_sample)
        chunk_overlap = min(overlap, chunk_size // 4)  # Ensure overlap doesn't exceed 25% of chunk

        file_ext = file_extension.lower()

        # Choose appropriate splitter based on file type
        if file_ext in ['.py', '.java', '.cpp', '.c', '.js', '.ts']:
            return PythonCodeTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif file_ext in ['.md', '.markdown']:
            return MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif file_ext in ['.html', '.htm']:
            # For HTML, use RecursiveCharacterTextSplitter with HTML-friendly separators
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["</body>", "</div>", "</section>", "</p>", "<br>", "\n\n", "\n", ". ", " ", ""]
            )
        elif file_ext in ['.csv']:
            # For CSV, use CSVTextSplitter if available
            return CSVTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        else:
            # Default to RecursiveCharacterTextSplitter for most text files
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

    @staticmethod
    def chunk_text_content(content: str, max_size_bytes: int, overlap: int = 100, file_extension: str = '.txt') -> List[str]:
        """Split text content into chunks using LangChain text splitters"""
        if not LANGCHAIN_AVAILABLE:
            # Fallback to simple splitting if LangChain not available
            return FileChunker._fallback_chunk_text_content(content, max_size_bytes, overlap)

        try:
            # Get appropriate splitter with content sampling for better size estimation
            splitter = FileChunker.get_appropriate_splitter(file_extension, max_size_bytes, overlap, content)

            if splitter is None:
                return FileChunker._fallback_chunk_text_content(content, max_size_bytes, overlap)

            # Split the text using LangChain with iterative size adjustment
            chunks = splitter.split_text(content)

            # Filter out empty chunks and ensure byte size limits with adaptive resizing
            filtered_chunks = []
            oversized_count = 0

            for chunk in chunks:
                if chunk.strip():
                    chunk_bytes = FileChunker.safe_byte_size(chunk)
                    if chunk_bytes <= max_size_bytes:
                        filtered_chunks.append(chunk)
                    else:
                        oversized_count += 1
                        # If chunk is still too large, split it further using simple method
                        sub_chunks = FileChunker._fallback_chunk_text_content(chunk, max_size_bytes, overlap)
                        filtered_chunks.extend(sub_chunks)

            # Log sizing efficiency for debugging
            if oversized_count > 0:
                efficiency = (len(chunks) - oversized_count) / len(chunks) * 100 if chunks else 0
                logger.debug(f"Chunk sizing efficiency: {efficiency:.1f}% ({oversized_count}/{len(chunks)} needed resizing)")

            return filtered_chunks if filtered_chunks else [content[:max_size_bytes]]

        except Exception as e:
            logger.warning(f"LangChain text splitting failed: {e}. Falling back to simple splitting.")
            return FileChunker._fallback_chunk_text_content(content, max_size_bytes, overlap)

    @staticmethod
    def _fallback_chunk_text_content(content: str, max_size_bytes: int, overlap: int = 100) -> List[str]:
        """Fallback text chunking method when LangChain is not available"""
        if not content:
            return []

        content_bytes = content.encode("utf-8")
        n = len(content_bytes)
        if n <= max_size_bytes:
            return [content]

        chunks = []
        start = 0

        while start < n:
            end = min(start + max_size_bytes, n)
            # Decode this segment safely
            segment = content_bytes[start:end].decode("utf-8", errors="replace")

            # Try to break at natural boundaries
            for delimiter in ['\n\n', '\n', '. ', '! ', '? ', ' ']:
                pos = segment.rfind(delimiter)
                if 0 < pos < len(segment):
                    end = start + pos + len(delimiter)
                    segment = content_bytes[start:end].decode("utf-8", errors="replace")
                    break

            if segment.strip():
                chunks.append(segment)

            # Advance with overlap in characters, not bytes
            start = max(0, end - overlap)

        return chunks

    @staticmethod
    def validate_chunk_sizes(chunks: List[str], max_size_bytes: int) -> Dict[str, Union[int, float, bool]]:
        """Validate chunk sizes and provide sizing statistics"""
        if not chunks:
            return {"valid": True, "total_chunks": 0, "oversized_count": 0, "efficiency": 100.0, "max_chunk_bytes": 0, "avg_chunk_bytes": 0.0}

        oversized_count = 0
        chunk_sizes = []

        for chunk in chunks:
            size_bytes = FileChunker.safe_byte_size(chunk)
            chunk_sizes.append(size_bytes)
            if size_bytes > max_size_bytes:
                oversized_count += 1

        total_chunks = len(chunks)
        efficiency = (total_chunks - oversized_count) / total_chunks * 100 if total_chunks > 0 else 100.0
        max_chunk_bytes = max(chunk_sizes) if chunk_sizes else 0
        avg_chunk_bytes = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0.0

        return {
            "valid": oversized_count == 0,
            "total_chunks": total_chunks,
            "oversized_count": oversized_count,
            "efficiency": efficiency,
            "max_chunk_bytes": max_chunk_bytes,
            "avg_chunk_bytes": avg_chunk_bytes,
        }

    @staticmethod
    def chunk_binary_file(file_path: str, max_size_bytes: int) -> List[bytes]:
        """Split binary file into chunks"""
        chunks = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(max_size_bytes)
                if not chunk:
                    break
                chunks.append(chunk)
        return chunks

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Enhanced file encoding detection with multiple strategies and BOM detection"""

        # Strategy 0: Check for Byte Order Marks (BOM) first
        try:
            with open(file_path, 'rb') as f:
                bom = f.read(4)

            # Check for common BOMs
            if bom.startswith(b'\xff\xfe\x00\x00'):
                logger.info("BOM detected: UTF-32 LE")
                return 'utf-32-le'
            elif bom.startswith(b'\x00\x00\xfe\xff'):
                logger.info("BOM detected: UTF-32 BE")
                return 'utf-32-be'
            elif bom.startswith(b'\xff\xfe'):
                logger.info("BOM detected: UTF-16 LE")
                return 'utf-16-le'
            elif bom.startswith(b'\xfe\xff'):
                logger.info("BOM detected: UTF-16 BE")
                return 'utf-16-be'
            elif bom.startswith(b'\xef\xbb\xbf'):
                logger.info("BOM detected: UTF-8")
                return 'utf-8'
        except Exception as e:
            logger.debug(f"BOM detection failed: {e}")

        # Strategy 1: Enhanced chardet detection with larger sample
        if CHARDET_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    # Read larger sample for better detection, up to 100KB
                    file_size = os.path.getsize(file_path)
                    sample_size = min(100000, file_size)
                    raw_data = f.read(sample_size)

                # Use chardet with incremental detection for better accuracy
                detector = chardet.UniversalDetector()

                # Feed data in chunks for better detection
                chunk_size = 8192
                for i in range(0, len(raw_data), chunk_size):
                    chunk = raw_data[i:i + chunk_size]
                    detector.feed(chunk)
                    if detector.done:
                        break

                detector.close()
                result = detector.result

                if result and result['encoding'] and result['confidence'] > 0.7:  # Higher confidence threshold
                    encoding = result['encoding'].lower()
                    # Enhanced mapping for common chardet results
                    encoding_map = {
                        'ascii': 'utf-8',  # ASCII is subset of UTF-8
                        'windows-1252': 'cp1252',
                        'windows-1251': 'cp1251',  # Cyrillic
                        'iso-8859-1': 'latin1',
                        'iso-8859-2': 'iso-8859-2',  # Central European
                        'iso-8859-15': 'iso-8859-15',  # Western European with Euro
                        'koi8-r': 'koi8-r',  # Russian
                        'gb2312': 'gb2312',  # Simplified Chinese
                        'big5': 'big5',  # Traditional Chinese
                        'shift_jis': 'shift_jis',  # Japanese
                        'euc-jp': 'euc-jp',  # Japanese
                        'euc-kr': 'euc-kr',  # Korean
                    }
                    detected = encoding_map.get(encoding, encoding)
                    logger.info(
                        f"Chardet detected encoding: {result['encoding']} (confidence: {result['confidence']:.2f}), using: {detected}")

                    # Validate detected encoding by trying to decode
                    try:
                        with open(file_path, 'r', encoding=detected) as test_f:
                            test_sample = test_f.read(1000)
                            if test_sample:  # Successfully read content
                                return detected
                    except (UnicodeDecodeError, UnicodeError):
                        logger.warning(f"Chardet detected encoding {detected} failed validation, trying fallback")

            except Exception as e:
                logger.warning(f"Enhanced chardet detection failed: {e}")

        # Strategy 2: Enhanced common encodings with statistical validation
        encodings_to_try = [
            'utf-8',  # Most common modern encoding
            'cp1252',  # Windows-1252 (common for Windows files)
            'latin1',  # ISO-8859-1 (fallback for Western European)
            'iso-8859-1',  # Alternative name for latin1
            'cp1251',  # Windows-1251 (Cyrillic)
            'iso-8859-2',  # Central European
            'iso-8859-15',  # Western European with Euro symbol
            'utf-16',  # Unicode with BOM
            'utf-16-le',  # Little endian UTF-16
            'utf-16-be',  # Big endian UTF-16
            'cp850',  # DOS Latin-1
            'cp437',  # Original IBM PC character set
            'macroman',  # Mac Roman (for older Mac files)
            'koi8-r',  # Russian
            'gb2312',  # Simplified Chinese
            'big5',  # Traditional Chinese
            'shift_jis',  # Japanese
            'euc-jp',  # Japanese EUC
            'euc-kr',  # Korean
        ]

        best_encoding = None
        best_score = 0

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Try to read a substantial portion of the file
                    try:
                        sample = f.read(10000)
                    except UnicodeDecodeError:
                        continue

                    # If we can read it and it contains actual content
                    if sample and len(sample.strip()) > 0:
                        # Score the encoding based on content characteristics
                        score = FileChunker._score_encoding_quality(sample, encoding)

                        if score > best_score:
                            best_score = score
                            best_encoding = encoding

                        # If we get a perfect score, return immediately
                        if score >= 100:
                            logger.info(f"High-quality encoding detected: {encoding} (score: {score})")
                            return encoding

            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.debug(f"Failed to test encoding {encoding}: {e}")
                continue

        if best_encoding and best_score > 50:  # Reasonable quality threshold
            logger.info(f"Best encoding detected: {best_encoding} (score: {best_score})")
            return best_encoding

        # Strategy 3: More conservative fallback with explicit error handling
        logger.error("Could not detect encoding reliably. File may be corrupted or use unsupported encoding.")
        # Rather than silently using latin1, raise an error to alert caller
        raise ValueError(f"Unable to detect valid encoding for file {file_path}. File may be corrupted, binary, or use an unsupported character encoding.")

    @staticmethod
    def _score_encoding_quality(sample: str, encoding: str) -> int:
        """Score the quality of text decoded with given encoding"""
        if not sample:
            return 0

        score = 50  # Base score for successful decoding

        # Check for common text characteristics
        printable_chars = sum(1 for c in sample if c.isprintable() or c.isspace())
        printable_ratio = printable_chars / len(sample) if len(sample) > 0 else 0

        # High printable character ratio is good
        if printable_ratio > 0.95:
            score += 30
        elif printable_ratio > 0.8:
            score += 20
        elif printable_ratio > 0.6:
            score += 10

        # Check for typical text patterns
        words = len(sample.split())
        if words > 10:  # Looks like text with words
            score += 10

        # Check for control characters (bad sign)
        control_chars = sum(1 for c in sample if ord(c) < 32 and c not in '\n\r\t')
        if control_chars == 0:
            score += 10
        elif control_chars < len(sample) * 0.01:  # Less than 1% control chars
            score += 5

        # Bonus for UTF-8 (modern standard)
        if encoding == 'utf-8':
            score += 5

        # Check for replacement characters (bad sign)
        if '\ufffd' in sample:
            score -= 20

        return min(100, max(0, score))

    @staticmethod
    def chunk_csv_file(file_path: str, max_size_bytes: int, max_rows_limit: int = 100000, max_memory_mb: float = 200.0) -> List[str]:
        """Split CSV file by rows while preserving structure with balanced memory and size limits"""
        # Balanced approach: allow larger files but with proper chunked processing
        file_size = os.path.getsize(file_path)

        # For very large files, use streaming approach regardless of memory limit
        max_file_size = int(max_memory_mb * 1024 * 1024 * 3)  # Allow 3x memory for large files with streaming

        if file_size > max_file_size:
            logger.warning(f"CSV file {file_path} ({file_size / 1024 / 1024:.1f}MB) is very large, using streaming approach")
            # Use streaming approach for oversized files
            return FileChunker._chunk_large_csv_streaming(file_path, max_size_bytes, max_rows_limit)

        # Detect encoding first
        encoding = FileChunker.detect_encoding(file_path)
        logger.info(f"Using encoding '{encoding}' for CSV file: {file_path}")

        if not PANDAS_AVAILABLE:
            return FileChunker._fallback_csv_text_chunking(file_path, encoding, max_size_bytes, max_memory_mb)

        try:
            # Read sample to estimate
            sample_df = pd.read_csv(
                file_path, encoding=encoding, on_bad_lines='skip',
                nrows=1000, low_memory=True, dtype=str, engine='python'
            )

            if sample_df.empty:
                logger.warning(f"CSV file appears empty: {file_path}")
                return []

            # Estimate memory per row
            sample_memory = sample_df.memory_usage(deep=True).sum()
            memory_per_row = max(sample_memory / len(sample_df), 100) if len(sample_df) > 0 else 1000

            # Calculate safe limits
            memory_limit_bytes = int(max_memory_mb * 1024 * 1024 * 0.7)
            safe_rows = min(max_rows_limit, int(memory_limit_bytes / memory_per_row * 0.8))
            safe_rows = max(10, safe_rows)  # Ensure minimum of 10 rows

            logger.info(f"Estimated {memory_per_row:.0f} bytes/row, reading up to {safe_rows} rows")

            # Read actual data
            df = pd.read_csv(
                file_path, encoding=encoding, on_bad_lines='skip',
                nrows=safe_rows, low_memory=True, dtype=str, engine='python'
            )

            if df.empty:
                logger.warning(f"DataFrame is empty after reading: {file_path}")
                return []

            # Check if streaming needed
            if len(df) >= max_rows_limit:
                logger.info(f"CSV has {len(df)} rows, switching to streaming")
                del df
                return FileChunker._chunk_large_csv_streaming(file_path, max_size_bytes, max_rows_limit)

            # Enhanced chunking with better loop protection
            chunks = []
            base_chunk_size = min(1000, max(10, len(df) // 10 + 1))

            i = 0
            iteration_count = 0
            last_successful_i = -1  # Track last successful position
            stalled_iterations = 0  # Count how many iterations we've been stuck
            max_stalled = 3  # Maximum stuck iterations before forcing progress

            # More conservative iteration limit
            max_iterations = min((len(df) // max(1, base_chunk_size)) * 3, 5000)

            while i < len(df) and iteration_count < max_iterations:
                iteration_count += 1
                remaining_rows = len(df) - i

                if remaining_rows <= 0:
                    logger.debug(f"No rows remaining at {i}")
                    break

                # Ensure positive chunk size with absolute minimum
                current_chunk_size = max(1, min(base_chunk_size, remaining_rows))

                # Extract chunk with bounds checking
                try:
                    chunk_df = df.iloc[i:i + current_chunk_size].copy()  # Use copy to avoid view warnings
                except Exception as iloc_err:
                    logger.error(f"Failed to extract chunk at row {i}: {iloc_err}")
                    i += 1  # Skip problematic row
                    continue

                if chunk_df.empty:
                    logger.warning(f"Empty chunk at row {i}, skipping")
                    i += max(1, current_chunk_size)
                    stalled_iterations += 1
                    continue

                # Generate CSV with error handling
                try:
                    chunk_csv = chunk_df.to_csv(index=False, encoding='utf-8')
                except Exception as csv_err:
                    logger.error(f"Failed to generate CSV at row {i}: {csv_err}")
                    i += 1
                    continue

                # Size reduction loop with strict limits
                reduction_attempts = 0
                max_reduction_attempts = 10
                min_chunk_size = 1

                while (len(chunk_csv.encode('utf-8')) > max_size_bytes and
                       current_chunk_size > min_chunk_size and
                       reduction_attempts < max_reduction_attempts):

                    # Reduce size more aggressively
                    current_chunk_size = max(min_chunk_size, current_chunk_size // 2)

                    if i + current_chunk_size > len(df):
                        current_chunk_size = max(min_chunk_size, len(df) - i)

                    if current_chunk_size < min_chunk_size:
                        break

                    try:
                        chunk_df = df.iloc[i:i + current_chunk_size].copy()
                        if chunk_df.empty:
                            break
                        chunk_csv = chunk_df.to_csv(index=False, encoding='utf-8')
                    except Exception:
                        break

                    reduction_attempts += 1

                # Handle oversized chunks that can't be reduced
                if reduction_attempts >= max_reduction_attempts:
                    logger.warning(f"Cannot reduce chunk at row {i}, skipping section")
                    skip_amount = min(5, max(1, current_chunk_size // 2))
                    i += skip_amount
                    stalled_iterations += 1

                    # Force major skip if we've been stalled too long
                    if stalled_iterations >= max_stalled:
                        logger.error(f"Stalled for {stalled_iterations} iterations, forcing large skip")
                        i += base_chunk_size
                        stalled_iterations = 0
                    continue

                # Successfully created chunk
                chunks.append(chunk_csv)
                logger.debug(f"Created CSV chunk: {len(chunk_df)} rows at position {i}")

                # Track progress with guaranteed advancement
                old_i = i
                # Ensure we always advance by at least 1 to prevent infinite loops
                advancement = max(1, current_chunk_size)
                i += advancement

                # Safety check: never go beyond dataframe bounds
                if i >= len(df):
                    logger.debug(f"Reached end of dataframe at position {i}")
                    break

                # Verify we made progress with stronger guarantees
                if i > old_i:
                    last_successful_i = i
                    stalled_iterations = 0  # Reset stall counter
                else:
                    # No progress - force forward with guaranteed minimum advancement
                    logger.error(f"No progress at row {old_i}, forcing advancement")
                    min_advancement = max(1, base_chunk_size // 10)  # Always at least 1
                    i = old_i + min_advancement
                    stalled_iterations += 1

                    # If stalled too long, make major jump with absolute guarantee
                    if stalled_iterations >= max_stalled:
                        logger.error(f"Repeated stalls, making emergency jump")
                        emergency_jump = max(10, base_chunk_size, len(df) // 100)  # At least 10 rows or 1% of data
                        i = max(last_successful_i + emergency_jump if last_successful_i >= 0 else old_i + emergency_jump, old_i + 10)
                        stalled_iterations = 0

                # Adaptive chunk sizing
                if current_chunk_size < base_chunk_size // 4:
                    base_chunk_size = max(10, current_chunk_size * 2)
                    logger.info(f"Adapted base chunk size to {base_chunk_size}")

            # Report stop reason
            if iteration_count >= max_iterations:
                logger.warning(f"CSV stopped at iteration limit ({max_iterations})")
            elif stalled_iterations >= max_stalled:
                logger.warning(f"CSV stopped due to repeated stalls")

            logger.info(f"Created {len(chunks)} CSV chunks from {len(df)} rows")
            return chunks

        except (pd.errors.EmptyDataError, pd.errors.ParserError) as pd_err:
            logger.warning(f"Pandas error for {file_path}: {pd_err}, using fallback")
            return FileChunker._fallback_csv_text_chunking(file_path, encoding, max_size_bytes, max_memory_mb)
        except MemoryError:
            logger.error(f"Memory error processing {file_path}")
            return []
        except Exception as e:
            logger.warning(f"CSV chunking failed: {e}, using fallback")
            return FileChunker._fallback_csv_text_chunking(file_path, encoding, max_size_bytes, max_memory_mb)

    @staticmethod
    def _chunk_large_csv_streaming(file_path: str, max_size_bytes: int, max_rows_limit: int) -> List[str]:
        """Stream process very large CSV files efficiently"""
        encoding = FileChunker.detect_encoding(file_path)
        chunks = []

        # Calculate appropriate chunk size for streaming
        # Use larger chunks for better efficiency but stay within memory limits
        stream_chunk_size = min(10000, max_rows_limit // 5)  # Process in 10k row chunks

        try:
            logger.info(f"Starting streaming CSV processing with chunk size: {stream_chunk_size}")

            chunk_reader = pd.read_csv(
                file_path,
                encoding=encoding,
                chunksize=stream_chunk_size,
                on_bad_lines='skip',
                dtype=str,
                low_memory=True,
                engine='python'  # More memory efficient
            )

            current_chunk_rows = []
            current_size = 0
            rows_processed = 0
            header_written = False
            original_header = None
            chunks_processed = 0
            max_chunks_to_process = (max_rows_limit // stream_chunk_size) + 50  # Safety limit
            consecutive_empty_chunks = 0
            max_empty_chunks = 10  # Maximum consecutive empty chunks before stopping

            logger.debug(f"Processing up to {max_chunks_to_process} chunks from CSV stream")

            try:
                for chunk_df in chunk_reader:
                    chunks_processed += 1

                    # Safety limits to prevent infinite loops
                    if chunks_processed > max_chunks_to_process:
                        logger.warning(f"Reached chunk processing limit ({max_chunks_to_process}), stopping streaming")
                        break

                    if rows_processed >= max_rows_limit:
                        logger.info(f"Reached row limit {max_rows_limit}, stopping")
                        break

                    # Handle empty chunks from malformed CSV data
                    if chunk_df.empty:
                        consecutive_empty_chunks += 1
                        logger.warning(f"Empty chunk encountered (#{consecutive_empty_chunks}) at chunk {chunks_processed}")

                        if consecutive_empty_chunks >= max_empty_chunks:
                            logger.error(f"Too many consecutive empty chunks ({consecutive_empty_chunks}), CSV may be malformed")
                            break
                        continue

                    # Reset empty chunk counter on successful read
                    consecutive_empty_chunks = 0

                    # Validate chunk data
                    try:
                        if len(chunk_df) == 0:
                            logger.warning(f"Zero-length chunk at chunk {chunks_processed}")
                            continue

                        # Get header from first valid chunk
                        if original_header is None:
                            original_header = chunk_df.columns.tolist()
                            if not original_header:
                                logger.error("CSV chunk has no columns, CSV may be malformed")
                                break

                        # Process chunk with error handling
                        chunk_csv = chunk_df.to_csv(index=False, header=not header_written)
                        chunk_size = len(chunk_csv.encode('utf-8'))

                        # Sanity check chunk size
                        if chunk_size == 0:
                            logger.warning(f"Generated zero-size chunk at chunk {chunks_processed}")
                            continue

                        if chunk_size > max_size_bytes * 10:  # Chunk is unreasonably large
                            logger.warning(f"Chunk size ({chunk_size / 1024:.1f}KB) is very large, may indicate malformed data")
                            # Try to process anyway but with caution

                    except Exception as chunk_processing_error:
                        logger.error(f"Error processing chunk {chunks_processed}: {chunk_processing_error}")
                        consecutive_empty_chunks += 1
                        if consecutive_empty_chunks >= max_empty_chunks:
                            logger.error("Too many chunk processing errors, stopping")
                            break
                        continue

                    # Check if this chunk fits in current output chunk
                    if current_size + chunk_size > max_size_bytes:
                        if current_chunk_rows:
                            try:
                                output_df = pd.DataFrame(current_chunk_rows, columns=original_header)
                                output_csv = output_df.to_csv(index=False)
                                chunks.append(output_csv)
                            except Exception as output_error:
                                logger.error(f"Error creating output chunk: {output_error}")
                                # Continue processing but log the error

                        current_chunk_rows = []
                        current_size = 0
                        header_written = True

                    # Additional size check after potential flush
                    if current_size > max_size_bytes:
                        logger.warning("Streaming chunk exceeded byte limit, flushing early.")
                        try:
                            output_df = pd.DataFrame(current_chunk_rows, columns=original_header)
                            chunks.append(output_df.to_csv(index=False))
                        except Exception as flush_error:
                            logger.error(f"Error during emergency flush: {flush_error}")

                        current_chunk_rows = []
                        current_size = 0

                    # Add current chunk rows to accumulator
                    try:
                        chunk_records = chunk_df.to_dict('records')
                        current_chunk_rows.extend(chunk_records)
                        current_size += chunk_size
                        rows_processed += len(chunk_df)

                        if not header_written:
                            header_written = True

                        if chunks_processed % 100 == 0:  # Log progress every 100 chunks
                            logger.debug(f"Processed {rows_processed} rows in {chunks_processed} chunks so far")

                    except Exception as accumulation_error:
                        logger.error(f"Error accumulating chunk data: {accumulation_error}")
                        consecutive_empty_chunks += 1
                        continue

            except Exception as reader_error:
                logger.error(f"Error reading from CSV chunk reader: {reader_error}")
                # Continue with whatever data we have

            # Add final chunk if any data remains
            if current_chunk_rows:
                try:
                    output_df = pd.DataFrame(current_chunk_rows, columns=original_header)
                    output_csv = output_df.to_csv(index=False)
                    chunks.append(output_csv)
                except Exception as final_error:
                    logger.error(f"Error creating final chunk: {final_error}")

            logger.info(f"Streaming processed {rows_processed} rows into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Streaming CSV processing failed: {e}")
            return []

    @staticmethod
    def _fallback_csv_text_chunking(file_path: str, encoding: str, max_size_bytes: int, max_memory_mb: float) -> List[str]:
        """Fallback text chunking for CSV files"""
        try:
            max_read_size = int(max_memory_mb * 1024 * 1024)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                # Read file in manageable chunks
                content_parts = []
                total_read = 0
                read_chunk_size = min(max_size_bytes * 4, 1024 * 1024)  # 1MB chunks

                while total_read < max_read_size:
                    chunk = f.read(read_chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)
                    total_read += len(chunk.encode('utf-8'))

                if total_read >= max_read_size:
                    logger.warning(f"CSV file truncated to {max_memory_mb}MB for processing")

                content = ''.join(content_parts)
                logger.info(f"Falling back to text chunking for CSV")
                return FileChunker.chunk_text_content(content, max_size_bytes, file_extension='.csv')
        except Exception as e2:
            logger.error(f"Failed to read CSV file even with fallback: {e2}")
            return []


class ThreadSafeEncodingCache:
    """Thread-safe LRU cache for file encodings"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = {}
        self._access_order = []  # Track access for LRU
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[str]:
        """Get encoding with LRU tracking"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
                self._access_order.append(key)
                return self._cache[key]
            return None
    
    def set(self, key: str, value: str):
        """Set encoding with automatic eviction"""
        with self._lock:
            # Remove if exists (to update access order)
            if key in self._cache:
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
            
            # Evict LRU items if at capacity
            while len(self._cache) >= self.max_size and self._access_order:
                lru_key = self._access_order.pop(0)
                self._cache.pop(lru_key, None)
            
            # Add new item
            self._cache[key] = value
            self._access_order.append(key)
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)


class Preprocess:
    """
    Main preprocessing class for handling large files and splitting them into chunks.

    Features:
    - Configurable file size threshold
    - Support for multiple file formats using unstructured.io
    - Intelligent chunking that preserves document structure
    - Progress tracking and logger
    """

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)

    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.max_size_bytes = int(self.config.max_file_size_mb * 1024 * 1024) - 1
        self.chunker = FileChunker()
        self._shutdown_event = threading.Event()

        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_split': 0,
            'chunks_created': 0,
            'total_size_processed': 0
        }

        # Thread management with proper synchronization and limits
        self._active_threads = set()  # Track active threads for cleanup
        self._threads_lock = threading.Lock()  # Protect thread set from concurrent access
        self._max_concurrent_threads = 5  # Limit to prevent resource exhaustion
        self._thread_semaphore = threading.Semaphore(self._max_concurrent_threads)

        # Thread-safe encoding cache
        self._encoding_cache = ThreadSafeEncodingCache(max_size=1000)

        # Thread synchronization for stats
        self._stats_lock = threading.Lock()  # Protect statistics from concurrent access

    def _update_stats(self, **updates):
        """Thread-safe method to update statistics"""
        with self._stats_lock:
            for key, value in updates.items():
                if key in self.stats:
                    self.stats[key] = int(self.stats[key]) + int(value)

    def _get_stats_copy(self):
        """Thread-safe method to get a copy of current statistics"""
        with self._stats_lock:
            return dict(self.stats)

    def _get_cached_encoding(self, file_path: str) -> Optional[str]:
        """Thread-safe method to get cached encoding"""
        return self._encoding_cache.get(file_path)

    def _cache_encoding(self, file_path: str, encoding: str):
        """Thread-safe method to cache encoding with size limits"""
        try:
            self._encoding_cache.set(file_path, encoding)
        except Exception as e:
            logger.debug(f"Failed to cache encoding for {file_path}: {e}")

    def cleanup_all_threads(self):
        """Clean up all active threads - call this on shutdown"""
        try:
            with self._threads_lock:
                active_threads = list(self._active_threads)

            if active_threads:
                logger.info(f"Cleaning up {len(active_threads)} active threads")

                # Signal shutdown to all threads
                self._shutdown_event.set()

                # Wait for threads to finish with timeout
                for thread in active_threads:
                    try:
                        thread.join(timeout=2.0)  # 2 second timeout per thread
                        if thread.is_alive():
                            logger.warning(f"Thread {thread.name} did not respond to shutdown signal")
                    except Exception as e:
                        logger.error(f"Error waiting for thread {thread.name}: {e}")

                # Clear the active threads set
                with self._threads_lock:
                    self._active_threads.clear()

                # Reset shutdown event
                self._shutdown_event.clear()

        except Exception as e:
            logger.error(f"Error during thread cleanup: {e}")

    def __del__(self):
        """Destructor to ensure threads are cleaned up"""
        try:
            self.cleanup_all_threads()
        except Exception:
            pass  # Ignore errors during destruction

    def detect_encoding_cached(self, file_path: str) -> str:
        """Thread-safe encoding detection with caching"""
        # Check cache first
        cached_encoding = self._get_cached_encoding(file_path)
        if cached_encoding:
            return cached_encoding

        try:
            # Detect encoding using FileChunker method
            detected_encoding = FileChunker.detect_encoding(file_path)

            # Cache the result for future use
            self._cache_encoding(file_path, detected_encoding)

            return detected_encoding
        except Exception as e:
            logger.warning(f"Encoding detection failed for {file_path}: {e}")
            # Return default encoding if detection fails
            return 'utf-8'

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup_all_threads()
        return False  # Don't suppress exceptions

    def _cleanup_timeout_thread(self, thread, timeout_seconds, operation_name):
        """Clean up a thread that may have timed out - thread-safe"""
        try:
            thread_completed = not thread.is_alive()

            # Atomic thread cleanup with proper synchronization
            with self._threads_lock:
                if thread in self._active_threads:
                    self._active_threads.discard(thread)

            if not thread_completed:
                logger.warning(f"{operation_name} timed out after {timeout_seconds}s, attempting cleanup")
                # Thread is daemon so it will be terminated when main process exits
                # Signal shutdown to any operations that check for it
                self._shutdown_event.set()

                # Wait a brief moment for thread to respond to shutdown signal
                try:
                    thread.join(timeout=0.5)
                    if not thread.is_alive():
                        logger.info(f"Thread {operation_name} responded to shutdown signal")
                        thread_completed = True
                except Exception:
                    pass  # Ignore join errors
                finally:
                    # Reset shutdown event for future operations
                    self._shutdown_event.clear()

                return None
            else:
                # Thread completed normally
                logger.debug(f"Thread {operation_name} completed successfully")
                return True

        except Exception as e:
            logger.error(f"Error during thread cleanup for {operation_name}: {e}")
            # Ensure thread is removed from tracking even on error
            with self._threads_lock:
                self._active_threads.discard(thread)
            return None

    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        return Path(file_path).suffix.lower() in self.config.supported_formats

    def needs_splitting(self, file_path: str) -> bool:
        """Check if file needs to be split"""
        return self.get_file_size(file_path) > self.max_size_bytes

    def _extract_text_from_elements(self, elements) -> str:
        """Helper method to extract text from unstructured elements"""
        content_dict = convert_to_dict(elements)
        text_content = []
        for element in content_dict:
            if 'text' in element:
                text_content.append(element['text'])
        return '\n'.join(text_content)

    def _try_partition_with_encoding(self, file_path: str, encoding: str) -> Optional[str]:
        """Helper method to try partitioning with a specific encoding"""
        try:
            elements = partition(filename=file_path, encoding=encoding)
            logger.info(f"Successfully extracted content with encoding {encoding}")
            return self._extract_text_from_elements(elements)
        except Exception as e:
            logger.debug(f"Failed with encoding {encoding}: {e}")
            return None

    def extract_content_with_unstructured(self, file_path: str) -> Optional[str]:
        """Extract content using unstructured.io with encoding fallback"""
        if not UNSTRUCTURED_AVAILABLE:
            return None

        # Strategy 1: Try with detected encoding first
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.csv']:
            detected_encoding = self.detect_encoding_cached(file_path)
            logger.info(f"Trying unstructured with detected encoding: {detected_encoding}")

            result = self._try_partition_with_encoding(file_path, detected_encoding)
            if result is not None:
                return result

            # Strategy 2: Try with common encodings as fallback
            encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            # Remove detected encoding if it's already in the list to avoid duplicate attempts
            if detected_encoding in encodings_to_try:
                encodings_to_try.remove(detected_encoding)

            for encoding in encodings_to_try:
                result = self._try_partition_with_encoding(file_path, encoding)
                if result is not None:
                    return result

        else:
            # Strategy 3: For non-text files, try default partition without encoding first
            try:
                elements = partition(filename=file_path)
                return self._extract_text_from_elements(elements)
            except UnicodeDecodeError as e:
                logger.warning(f"Unicode decode error with unstructured from {file_path}: {e}")
                # Try with UTF-8 encoding as fallback for binary files
                try:
                    elements = partition(filename=file_path, encoding='utf-8')
                    return self._extract_text_from_elements(elements)
                except Exception as e2:
                    logger.warning(f"UTF-8 fallback also failed: {e2}")
            except Exception as e:
                logger.warning(f"Failed to extract content with unstructured from {file_path}: {e}")

        logger.warning(f"All encoding strategies failed for {file_path}")
        return None

    def extract_content_fallback(self, file_path: str, max_size_mb: float = 50.0) -> Optional[str]:
        """Fallback content extraction for text files with strict limits and proper error handling"""
        # Check file size before attempting to read
        file_size = self.get_file_size(file_path)
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        if file_size > max_size_bytes:
            logger.error(f"File {file_path} ({file_size / 1024 / 1024:.1f}MB) exceeds maximum safe read size ({max_size_mb}MB). Processing aborted.")
            # Don't attempt to process oversized files as it leads to resource exhaustion
            raise ValueError(f"File too large for safe processing: {file_size / 1024 / 1024:.1f}MB > {max_size_mb}MB")

        # Try to detect encoding with proper error handling
        try:
            encoding = self.detect_encoding_cached(file_path)
        except ValueError as e:
            logger.error(f"Encoding detection failed for {file_path}: {e}")
            return None

        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read text content from {file_path} with encoding {encoding}: {e}")
            # More conservative fallback strategy
            conservative_encodings = ['utf-8', 'cp1252', 'iso-8859-1']
            for fallback_encoding in conservative_encodings:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding, errors='strict') as f:  # Use strict mode
                        # Test read first 1KB to validate encoding
                        test_content = f.read(1024)
                        if not test_content:
                            logger.warning(f"File appears empty: {file_path}")
                            return ""

                        # If test passes, read full file
                        f.seek(0)
                        content = f.read()
                        logger.info(f"Successfully read {file_path} with encoding {fallback_encoding}")
                        return content

                except UnicodeDecodeError as decode_error:
                    logger.debug(f"Encoding {fallback_encoding} failed with decode error: {decode_error}")
                    continue
                except (IOError, OSError) as io_error:
                    logger.error(f"IO error reading {file_path} with {fallback_encoding}: {io_error}")
                    return None
                except Exception as unexpected_error:
                    logger.warning(f"Unexpected error with encoding {fallback_encoding}: {unexpected_error}")
                    continue

            # If all encodings fail, it's likely not a text file
            logger.error(f"Could not read {file_path} with any supported encoding. File may be binary or corrupted.")
            return None

    def _validate_file_path(self, file_path: str, allowed_base_paths: list = None, _visited_paths: set = None, _depth: int = 0) -> Path:
        """Validate file path to prevent path traversal attacks and symlink loops"""
        if _visited_paths is None:
            _visited_paths = set()

        # Prevent excessive recursion depth
        if _depth > 20:
            raise ValueError(f"Symlink chain too deep (max 20): {file_path}")

        try:
            # Get the absolute path without following symlinks first
            path = Path(file_path).resolve(strict=False)

            # Normalize path to prevent bypass attempts
            path = path.absolute()

            # More robust path traversal detection
            normalized_parts = []
            for part in path.parts:
                if part in ('..', '.', ''):
                    continue
                normalized_parts.append(part)

            if len(normalized_parts) != len([p for p in path.parts if p not in ('', '.')]):
                raise ValueError(f"Path traversal attempt detected in: {file_path}")

            # Ensure path exists and is a file
            if not path.exists():
                raise ValueError(f"File does not exist: {file_path}")
            if not path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # Enhanced symlink loop detection using inode tracking
            if path.is_symlink():
                try:
                    # Use device + inode for more reliable loop detection
                    stat_info = path.lstat()
                    path_id = (stat_info.st_dev, stat_info.st_ino)
                    if path_id in _visited_paths:
                        raise ValueError(f"Symlink loop detected involving: {file_path}")
                    _visited_paths.add(path_id)

                    real_path = (path.parent / os.readlink(path)).resolve(strict=False)
                    logger.warning(f"Following symlink {path} -> {real_path}")

                    # Recursively validate with depth tracking
                    return self._validate_file_path(str(real_path), allowed_base_paths, _visited_paths, _depth + 1)

                except OSError as e:
                    raise ValueError(f"Cannot access symlink {file_path}: {e}")

            # Validate against allowed base paths with proper resolution
            if allowed_base_paths:
                is_allowed = False
                for base_path in allowed_base_paths:
                    try:
                        base_resolved = Path(base_path).resolve()
                        # Use resolve() to handle any symlinks in base path too
                        path.relative_to(base_resolved)
                        is_allowed = True
                        break
                    except (ValueError, OSError):
                        continue

                if not is_allowed:
                    raise ValueError(f"File path outside allowed directories: {file_path}")

            return path

        except (OSError, ValueError) as e:
            # Preserve original exception type and traceback for better debugging
            if isinstance(e, ValueError):
                raise  # Re-raise ValueError as-is
            else:
                # Wrap OS errors with more context but preserve original type
                raise type(e)(f"File system error validating {file_path}: {str(e)}") from e
        except Exception as e:
            # For unexpected exceptions, provide more context but preserve original exception chain
            raise RuntimeError(f"Unexpected error validating file path {file_path}: {str(e)}") from e

    def _check_disk_space(self, file_path: Path, estimated_chunks: int = None) -> bool:
        """Check if there's enough disk space for processing with improved accuracy"""
        try:
            stat = shutil.disk_usage(file_path.parent)
            available_bytes = stat.free
            file_size = Preprocess.get_file_size(str(file_path))

            # Improved chunk estimation
            if estimated_chunks is None:
                # Base estimation on actual chunk overlap and file characteristics
                base_chunks = max(1, int(file_size / self.max_size_bytes))
                overlap_factor = 1 + (self.config.chunk_overlap / self.max_size_bytes)
                estimated_chunks = int(base_chunks * overlap_factor) + 1

            # Conservative space estimation with filesystem overhead accounting
            file_ext = file_path.suffix.lower()

            # More conservative multipliers to prevent out-of-space crashes
            if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
                # Conservative text file processing
                base_multiplier = 3.0  # Increased from 2.0
                if file_size > 10 * 1024 * 1024:  # Reduced threshold from 50MB to 10MB
                    base_multiplier += 1.0
                space_multiplier = base_multiplier

            elif file_ext in ['.pdf', '.docx', '.doc', '.pptx', '.ppt']:
                # Very conservative for document extraction
                base_multiplier = 10.0  # Increased from 6.0
                if file_size > 5 * 1024 * 1024:  # Reduced threshold from 10MB to 5MB
                    base_multiplier += 5.0
                space_multiplier = base_multiplier

            elif file_ext in ['.csv', '.xlsx', '.xls']:
                # Very conservative for CSV/Excel processing
                base_multiplier = 8.0  # Increased from 4.0
                if file_size > 50 * 1024 * 1024:  # Reduced threshold from 100MB to 50MB
                    base_multiplier += 10.0  # Significantly increased
                space_multiplier = base_multiplier

            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                # Conservative for binary files
                space_multiplier = 2.0  # Increased from 1.3

            elif file_ext in ['.log', '.dat', '.bin']:
                # Conservative for log/data files
                space_multiplier = 4.0  # Increased from 2.5

            else:
                # Very conservative for unknown file types
                space_multiplier = 5.0  # Increased from 2.0

            # Conservative space calculation with filesystem overhead
            base_space_needed = file_size * space_multiplier * estimated_chunks

            # Filesystem overhead (typically 10-15% for journaled filesystems)
            filesystem_overhead = int(base_space_needed * 0.15)

            # Much larger safety buffer
            min_safety_buffer = 500 * 1024 * 1024  # 500MB minimum (increased from 100MB)
            adaptive_buffer = max(min_safety_buffer, int(base_space_needed * 0.3))  # 30% buffer (increased from 15%)

            # Additional buffer for complex processing
            if file_ext in ['.pdf', '.docx', '.doc', '.csv', '.xlsx'] and file_size > 10 * 1024 * 1024:  # Reduced threshold
                adaptive_buffer += 1024 * 1024 * 1024  # Extra 1GB for complex processing (increased from 200MB)

            # Include all components in space calculation
            base_space_needed += filesystem_overhead

            total_space_needed = base_space_needed + adaptive_buffer

            if available_bytes < total_space_needed:
                logger.error(
                    f"Insufficient disk space. Available: {available_bytes / 1024 / 1024:.1f}MB, "
                    f"Estimated needed: {total_space_needed / 1024 / 1024:.1f}MB "
                    f"(file: {file_size / 1024 / 1024:.1f}MB, multiplier: {space_multiplier}x, chunks: {estimated_chunks})"
                )
                return False

            logger.debug(
                f"Disk space check passed. Available: {available_bytes / 1024 / 1024:.1f}MB, "
                f"Estimated needed: {total_space_needed / 1024 / 1024:.1f}MB"
            )
            return True
        except OSError as e:
            logger.warning(f"Could not check disk space: {e}")
            return True  # Proceed if we can't check

    def _safe_delete_original_file(self, file_path: Path, output_files: List[str]) -> bool:
        """
        Safely delete original file using atomic operations and proper locking.
        Eliminates race conditions and TOCTOU vulnerabilities.

        Args:
            file_path: Path to original file to delete
            output_files: List of chunk files that were created

        Returns:
            bool: True if file was successfully deleted, False otherwise
        """
        if not file_path.exists():
            logger.warning(f"Original file {file_path} no longer exists")
            return False

        if not output_files:
            logger.warning(f"No chunk files created for {file_path}, not deleting original")
            return False

        # Initialize variables that may be used in finally blocks
        lock_fd = None
        lock_path = None
        file_locked = False

        try:
            # Create a unique lock file using atomic file creation
            lock_filename = f".{file_path.name}.{uuid.uuid4().hex[:8]}.delete_lock"
            lock_path = file_path.parent / lock_filename

            # Attempt to create lock file atomically
            try:
                lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                try:
                    # Write process info to lock file for debugging
                    lock_info = f"pid:{os.getpid()},time:{time.time()},file:{file_path.name}"
                    os.write(lock_fd, lock_info.encode('utf-8'))
                    os.fsync(lock_fd)  # Force write to disk
                except Exception as write_err:
                    logger.debug(f"Failed to write lock info: {write_err}")
            except FileExistsError:
                # Another process is already deleting this file
                logger.info(f"File deletion already in progress for {file_path}")
                return False
            except OSError as lock_err:
                logger.error(f"Failed to create lock file for {file_path}: {lock_err}")
                return False

            try:
                # Apply file lock for additional safety (non-blocking)
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    file_locked = True
                except (OSError, ImportError):
                    # fcntl might not be available on all platforms
                    file_locked = False
                    logger.debug("File locking not available, continuing without flock")

                # Validate all chunks exist and are readable with atomic checks
                chunk_validation_results = []
                for chunk_path_str in output_files:
                    chunk_path = Path(chunk_path_str)
                    try:
                        # Use atomic stat operation to get file info
                        chunk_stat = chunk_path.stat()
                        if chunk_stat.st_size == 0:
                            logger.error(f"Chunk file is empty: {chunk_path}")
                            return False

                        # Test file readability with minimal read
                        try:
                            with open(chunk_path, 'rb') as test_file:
                                test_data = test_file.read(64)  # Read first 64 bytes
                                if not test_data:
                                    logger.error(f"Cannot read chunk file: {chunk_path}")
                                    return False
                        except Exception as read_err:
                            logger.error(f"Failed to validate chunk {chunk_path}: {read_err}")
                            return False

                        # Store validation result with file metadata
                        chunk_validation_results.append({
                            'path': chunk_path,
                            'size': chunk_stat.st_size,
                            'mtime': chunk_stat.st_mtime,
                            'validated': True
                        })

                    except OSError as chunk_err:
                        logger.error(f"Cannot access chunk file {chunk_path}: {chunk_err}")
                        return False

                # Final verification: re-check all chunks are still valid
                for chunk_info in chunk_validation_results:
                    try:
                        current_stat = chunk_info['path'].stat()
                        # Check if file was modified during validation
                        if current_stat.st_mtime != chunk_info['mtime']:
                            logger.error(f"Chunk file was modified during validation: {chunk_info['path']}")
                            return False
                        if current_stat.st_size != chunk_info['size']:
                            logger.error(f"Chunk file size changed during validation: {chunk_info['path']}")
                            return False
                    except OSError as recheck_err:
                        logger.error(f"Chunk file became inaccessible: {chunk_info['path']}: {recheck_err}")
                        return False

                # All chunks validated - now safely delete original file
                try:
                    # Final check: ensure original file still exists before deletion
                    if not file_path.exists():
                        logger.warning(f"Original file {file_path} disappeared during validation")
                        return False

                    # Get file info before deletion for logger
                    original_stat = file_path.stat()
                    original_size = original_stat.st_size

                    # Atomic deletion
                    os.remove(str(file_path))

                    # Verify deletion was successful
                    if file_path.exists():
                        logger.error(f"File deletion appeared to succeed but file still exists: {file_path}")
                        return False

                    logger.info(f"Successfully deleted original file: {file_path} ({original_size} bytes)")
                    return True

                except OSError as delete_err:
                    logger.error(f"Failed to delete original file {file_path}: {delete_err}")
                    return False

            finally:
                # Cleanup: release file lock if acquired
                if file_locked and lock_fd is not None:
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    except (OSError, ImportError):
                        pass  # Ignore cleanup errors

        except Exception as outer_err:
            logger.error(f"Unexpected error during safe file deletion for {file_path}: {outer_err}")
            return False

        finally:
            # Always cleanup lock file and file descriptor
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass  # Ignore close errors

            if lock_path is not None and lock_path.exists():
                try:
                    os.remove(str(lock_path))
                except OSError:
                    pass  # Ignore cleanup errors

    def process_file(self, file_path: str) -> Dict[str, Union[str, List[str]]]:
        """Process a single file"""
        try:
            file_path = self._validate_file_path(file_path)
        except ValueError as e:
            logger.error(str(e))
            return {'status': 'error', 'error': str(e)}

        logger.info(f"Processing file: {file_path}")

        if not self.is_supported_format(str(file_path)):
            logger.warning(f"Unsupported file format: {file_path.suffix}")
            return {'status': 'skipped', 'reason': 'unsupported_format'}

        file_size = Preprocess.get_file_size(str(file_path))
        self._update_stats(total_size_processed=file_size, files_processed=1)
        if not self.needs_splitting(str(file_path)):
            # File is small enough, no processing needed
            logger.info(f"File size ({file_size / 1024 / 1024:.2f} MB) is within threshold. No splitting needed.")
            return {'status': 'no_processing_needed', 'size_mb': file_size / 1024 / 1024}

        # Check disk space before processing large files
        if not self._check_disk_space(file_path):
            error_msg = 'Insufficient disk space for processing'
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # File needs splitting
        logger.info(f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds threshold. Splitting...")

        # Try to extract content intelligently (but skip for CSV files)
        content = None
        if file_path.suffix.lower() != '.csv':
            content = self.extract_content_with_unstructured(str(file_path))

        output_files = []
        # in-memory processing
        if content is not None and not output_files:
            # Add timeout protection for in-memory chunking using threading
            logger.info(f"Using in-memory text chunking for {file_path} (content length: {len(content)} chars)")
            try:
                def chunk_content_with_timeout(content_text, max_bytes, overlap, result_queue_obj):
                    import gc
                    try:
                        # Monitor memory usage for in-memory operations
                        try:
                            import psutil
                            process = psutil.Process(os.getpid())
                            initial_memory = process.memory_info().rss / 1024 / 1024
                            max_memory_increase = min(500, len(content_text) / 1024 / 1024 * 2)  # Allow 2x content size or 500MB
                        except ImportError:
                            # Fallback if psutil not available
                            max_memory_increase = 500
                            initial_memory = 0

                        # Estimate content memory usage
                        content_size_mb = len(content_text.encode('utf-8')) / 1024 / 1024
                        logger.debug(f"Processing {content_size_mb:.1f}MB content in memory")

                        if content_size_mb > 100:  # > 100MB content
                            logger.warning(f"Large content ({content_size_mb:.1f}MB) being processed in memory")

                        chunk_result = FileChunker.chunk_text_content(
                            content_text,
                            max_bytes,
                            overlap,
                            file_extension=str(file_path.suffix)  # Use actual file extension
                        )

                        # Check memory usage after chunking
                        try:
                            if 'process' in locals():
                                final_memory = process.memory_info().rss / 1024 / 1024
                                memory_increase = final_memory - initial_memory
                                if memory_increase > max_memory_increase:
                                    logger.warning(f"In-memory chunking used {memory_increase:.1f}MB (limit: {max_memory_increase:.1f}MB)")
                        except:
                            pass

                        result_queue_obj.put(("success", chunk_result))

                    except MemoryError:
                        logger.error("Memory error during in-memory chunking")
                        gc.collect()  # Force cleanup
                        result_queue_obj.put(("error", MemoryError("In-memory chunking memory limit exceeded")))
                    except Exception as chunk_error:
                        logger.error(f"Error in in-memory chunking: {chunk_error}")
                        result_queue_obj.put(("error", chunk_error))
                    finally:
                        # Force garbage collection to free memory
                        gc.collect()

                # Set reasonable timeout for in-memory chunking (30 seconds max)
                timeout_seconds = min(30, len(content) // 100000 + 5)  # 5s base + 1s per 100k chars

                # Acquire semaphore to limit concurrent threads
                if not self._thread_semaphore.acquire(blocking=False):
                    logger.warning(f"Thread limit ({self._max_concurrent_threads}) reached, processing {file_path} without threading")
                    # Process directly without threading as fallback
                    try:
                        chunks = FileChunker.chunk_text_content(
                            content,
                            self.max_size_bytes,
                            self.config.chunk_overlap,
                            file_extension=str(file_path.suffix)
                        )
                    except Exception as direct_err:
                        logger.error(f"Direct chunking failed: {direct_err}")
                        chunks = [content[:self.max_size_bytes * 4]]
                else:
                    try:
                        result_queue = queue.Queue()
                        chunk_thread = threading.Thread(
                            target=chunk_content_with_timeout,
                            args=(content, self.max_size_bytes, self.config.chunk_overlap, result_queue)
                        )
                        chunk_thread.daemon = True

                        # Thread-safe addition to active threads set
                        with self._threads_lock:
                            self._active_threads.add(chunk_thread)

                        chunk_thread.start()
                        chunk_thread.join(timeout_seconds)
                    finally:
                        # Always release semaphore
                        self._thread_semaphore.release()

                    # Only do cleanup and result retrieval if threading was used
                    chunks = None
                    cleanup_result = self._cleanup_timeout_thread(chunk_thread, timeout_seconds, f"In-memory chunking for {file_path}")
                    if cleanup_result is None:
                        # Thread timed out - emergency fallback
                        chunks = [content[:self.max_size_bytes * 4]]  # Take first part that should fit
                    else:
                        try:
                            status, result = result_queue.get_nowait()
                            if status == "success":
                                chunks = result
                            else:
                                raise result
                        except queue.Empty:
                            logger.error(f"In-memory chunking failed to produce results for {file_path}")
                            chunks = [content[:self.max_size_bytes * 4]]

            except Exception as e:
                logger.error(f"In-memory chunking failed for {file_path}: {e}")
                # Emergency fallback - just create one large chunk
                chunks = [content[:self.max_size_bytes * 4]]  # Take first part that should fit

            # Save chunks in same directory as original file
            for i, chunk in enumerate(chunks, 1):
                # For PDFs and other document formats, save extracted content as .txt
                if file_path.suffix.lower() in ['.pdf', '.docx', '.doc', '.pptx', '.ppt']:
                    chunk_filename = f"{file_path.stem}_part{i}.txt"
                else:
                    chunk_filename = f"{file_path.stem}_part{i}{file_path.suffix}"
                chunk_path = file_path.parent / chunk_filename

                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)

                output_files.append(str(chunk_path))
                logger.info(f"Created chunk: {chunk_path}")

        elif file_path.suffix.lower() == '.csv' and not output_files:
            # Special handling for CSV files (only if streaming didn't handle it)
            logger.info(f"Using CSV-specific chunking for {file_path}")
            chunks = self.chunker.chunk_csv_file(str(file_path), self.max_size_bytes)

            if not chunks:
                logger.error(f"Failed to create chunks for CSV file: {file_path}")
                return {
                    'status': 'error',
                    'error': 'Failed to chunk CSV file - encoding or format issues'
                }

            for i, chunk in enumerate(chunks, 1):
                chunk_filename = f"{file_path.stem}_part{i}.csv"
                chunk_path = file_path.parent / chunk_filename

                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)

                output_files.append(str(chunk_path))
                logger.info(f"Created CSV chunk: {chunk_path}")

        elif file_path.suffix.lower() in ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'] and not output_files:
            # Document formats - if unstructured failed, return error instead of binary splitting
            logger.error(f"Failed to extract content from document {file_path}. Cannot perform binary splitting on structured documents.")
            return {
                'status': 'error',
                'error': f'Failed to extract content from {file_path.suffix} file. Document may be corrupted or password protected.'
            }

        elif not output_files:
            if file_path.suffix.lower() in ['.xlsx', '.xls', '.pptx', '.docx', '.doc']:
                return {
                    'status': 'error',
                    'error': f'Binary splitting not supported for {file_path.suffix} files.'
                }

            # Binary file splitting - only for truly binary files like images (and only if streaming didn't handle it)
            chunks = self.chunker.chunk_binary_file(str(file_path), self.max_size_bytes)

            for i, chunk in enumerate(chunks, 1):
                chunk_filename = f"{file_path.stem}_part{i}{file_path.suffix}"
                chunk_path = file_path.parent / chunk_filename

                with open(chunk_path, 'wb') as f:
                    f.write(chunk)

                output_files.append(str(chunk_path))
                logger.info(f"Created binary chunk: {chunk_path}")

        # Delete original file if configured to do so and all chunks were created successfully
        deleted_original = False
        if self.config.delete_original and output_files:
            deleted_original = self._safe_delete_original_file(file_path, output_files)

        self._update_stats(files_split=1, chunks_created=len(output_files))

        return {
            'status': 'split',
            'chunks': len(output_files),
            'output_files': output_files,
            'original_deleted': deleted_original
        }

    def process(self, root_dir: str, recursive: bool = True) -> Dict:
        """Traverse directory and process all files"""
        root_path = Path(root_dir)

        if not root_path.exists():
            raise ValueError(f"Directory does not exist: {root_dir}")

        logger.info(f"Starting to traverse directory: {root_dir}")
        processed_files = {}

        # Resource limits
        max_total_bytes = int(self.config.max_total_size_gb * 1024 * 1024 * 1024)
        total_size_processed = 0
        files_processed = 0

        def iter_files(root, recursive=True):
            pattern = "**/*" if recursive else "*"
            for file_path in Path(root).glob(pattern):
                if file_path.is_symlink() and file_path.is_dir():
                    continue
                if file_path.is_file():
                    yield file_path

        for file_path in itertools.islice(iter_files(root_dir, recursive), self.config.max_files_per_run):
            if file_path.is_file():
                # Check resource limits
                if files_processed >= self.config.max_files_per_run:
                    logger.warning(f"Reached maximum file limit ({self.config.max_files_per_run}). Stopping.")
                    break

                file_size = Preprocess.get_file_size(str(file_path))
                if total_size_processed + file_size > max_total_bytes:
                    logger.warning(f"Would exceed total size limit ({self.config.max_total_size_gb}GB). Stopping.")
                    break

                try:
                    result = self.process_file(str(file_path))
                    processed_files[str(file_path)] = result
                    files_processed += 1
                    total_size_processed += file_size
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    processed_files[str(file_path)] = {'status': 'error', 'error': str(e)}

        summary = {
            'config': {
                'max_file_size_mb': self.config.max_file_size_mb,
                'delete_original': self.config.delete_original,
                'supported_formats': self.config.supported_formats
            },
            'statistics': self._get_stats_copy(),  # Thread-safe stats access
            'processed_files': processed_files
        }

        logger.info(f"Processing complete.")
        return summary

    def print_statistics(self):
        """Print processing statistics (thread-safe)"""
        stats = self._get_stats_copy()
        print("\n" + "=" * 50)
        print("PROCESSING STATISTICS")
        print("=" * 50)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Files split: {stats['files_split']}")
        print(f"Chunks created: {stats['chunks_created']}")
        print(f"Total size processed: {stats['total_size_processed'] / 1024 / 1024:.2f} MB")
        print("=" * 50)


# Example usage
if __name__ == "__main__":
    # Custom configuration
    config = ProcessingConfig(
        max_file_size_mb=0.5,  # 500 KB threshold for demo
        chunk_overlap=50,
        preserve_structure=True,
        delete_original=True  # Delete original files after splitting
    )

    # Initialize preprocessor
    preprocessor = Preprocess(config)

    # Process a directory
    # result = preprocessor.traverse_and_process("path/to/your/directory")

    # Process a single file
    # result = preprocessor.process_file("path/to/your/large_file.pdf")
