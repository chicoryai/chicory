import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import type { TrailItem } from "~/types/auditTrail";

// Initialize S3 client - works for both AWS S3 (cloud) and MinIO (local)
// When S3_ENDPOINT_URL is set, use custom endpoint with path-style access (MinIO)
// When not set, use standard AWS S3 with auto-loaded credentials (IAM role, env vars, etc.)
const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-west-2',
  ...(process.env.S3_ENDPOINT_URL && {
    endpoint: process.env.S3_ENDPOINT_URL,
    forcePathStyle: true, // Required for MinIO/S3-compatible storage
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
    },
  }),
});

// Parse S3 URL to extract bucket and key
function parseS3Url(s3Url: string): { bucket: string; key: string } | null {
  if (s3Url.startsWith('s3://')) {
    const url = s3Url.replace('s3://', '');
    const [bucket, ...keyParts] = url.split('/');
    const key = keyParts.join('/');
    
    if (!bucket || !key) {
      return null;
    }
    
    return { bucket, key };
  }
  return null;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { taskId } = params;
  
  if (!taskId) {
    return json({ error: "Task ID is required" }, { status: 400 });
  }

  // Get the S3 URL from query params (passed by the component)
  const url = new URL(request.url);
  const auditTrailUrl = url.searchParams.get("url");
  const bucketParam = url.searchParams.get("bucket");
  const keyParam = url.searchParams.get("key");
    
  if (!auditTrailUrl && !(bucketParam && keyParam)) {
    // Return empty array if no trail reference exists
    return json({ trail: [] });
  }

  try {
    // Handle both S3 and HTTPS URLs
    if (bucketParam && keyParam) {
      console.log("Fetching from S3 bucket/key:", bucketParam, keyParam);

      const command = new GetObjectCommand({
        Bucket: bucketParam,
        Key: keyParam
      });

      const response = await s3Client.send(command);
      const bodyString = await response.Body?.transformToString();

      if (!bodyString) {
        return json({ error: "Empty response from S3" }, { status: 500 });
      }

      const trailData: TrailItem[] = JSON.parse(bodyString);
      return json({ trail: trailData });

    } else if (auditTrailUrl && auditTrailUrl.startsWith('s3://')) {
      // Parse S3 URL
      const s3Parts = parseS3Url(auditTrailUrl);
      
      if (!s3Parts) {
        return json({ error: "Invalid S3 URL format" }, { status: 400 });
      }

      console.log("Fetching from S3:", s3Parts.bucket, s3Parts.key);

      // Fetch from S3 using SDK
      const command = new GetObjectCommand({
        Bucket: s3Parts.bucket,
        Key: s3Parts.key
      });

      const response = await s3Client.send(command);
      
      // Convert stream to string
      const bodyString = await response.Body?.transformToString();
      
      if (!bodyString) {
        return json({ error: "Empty response from S3" }, { status: 500 });
      }

      // Parse JSON
      const trailData: TrailItem[] = JSON.parse(bodyString);
      console.log("Successfully fetched trail data with", trailData.length, "items");
      
      return json({ trail: trailData });
      
    } else if (auditTrailUrl && auditTrailUrl.startsWith('https://')) {
      // Fallback to direct HTTPS fetch for backward compatibility
      console.log("Fetching from HTTPS URL:", auditTrailUrl);
      
      const response = await fetch(auditTrailUrl);
      
      if (!response.ok) {
        console.error("Failed to fetch from HTTPS:", response.status, response.statusText);
        return json({ error: `Failed to fetch: ${response.status}` }, { status: 500 });
      }

      const trailData: TrailItem[] = await response.json();
      console.log("Successfully fetched trail data with", trailData.length, "items");
      
      return json({ trail: trailData });
      
    } else {
      return json({ error: "URL must start with s3:// or https://" }, { status: 400 });
    }
    
  } catch (error) {
    console.error("Error fetching audit trail:", error);
    
    // Handle specific AWS errors
    if (error && typeof error === 'object' && 'name' in error) {
      const awsError = error as { name: string; message: string; $metadata?: any };
      
      if (awsError.name === 'NoSuchKey') {
        console.log(`Trail file not found at: s3://${auditTrailUrl.replace('s3://', '')}`);
        return json({ 
          error: "Audit trail not yet available. It will be uploaded after the task completes.", 
          trail: [] 
        }, { status: 404 });
      } else if (awsError.name === 'AccessDenied') {
        return json({ error: "Access denied to S3 object" }, { status: 403 });
      } else if (awsError.name === 'NoSuchBucket') {
        return json({ error: "S3 bucket not found" }, { status: 404 });
      }
      
      // Log AWS error details for debugging
      console.error("AWS Error details:", {
        name: awsError.name,
        message: awsError.message,
        metadata: awsError.$metadata
      });
    }
    
    return json({ 
      error: error instanceof Error ? error.message : "Failed to fetch audit trail",
      trail: [] 
    }, { status: 500 });
  }
}
