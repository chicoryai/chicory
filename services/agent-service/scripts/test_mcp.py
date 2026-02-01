#!/usr/bin/env python3
"""
Test MCP server protocol compliance.

Usage:
    python scripts/test_mcp.py [--url URL] [--api-key KEY]

Environment variables:
    CHICORY_MCP_BASE_URL - Base URL (default: http://localhost:3000)
    CHICORY_MCP_API_KEY - API key for authentication
"""
import argparse
import json
import os
import sys
import httpx


def test_mcp_server(base_url: str, api_key: str) -> bool:
    """Test MCP server protocol compliance."""

    mcp_url = f"{base_url}/mcp/platform"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    print(f"\n{'='*60}")
    print(f"Testing MCP Server: {mcp_url}")
    print(f"{'='*60}\n")

    all_passed = True

    # Test 1: Initialize handshake
    print("1. Testing 'initialize' method...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-test-client",
                "version": "1.0.0"
            }
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(mcp_url, headers=headers, json=init_request)

            print(f"   Status: {response.status_code}")

            if response.status_code != 200:
                print(f"   ❌ FAILED - Expected 200, got {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                all_passed = False
            else:
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2)[:500]}")

                    if "result" in data:
                        print("   ✅ PASSED - Valid initialize response")
                        server_info = data.get("result", {}).get("serverInfo", {})
                        print(f"   Server: {server_info.get('name', 'unknown')} v{server_info.get('version', '?')}")
                    elif "error" in data:
                        print(f"   ❌ FAILED - Server returned error: {data['error']}")
                        all_passed = False
                    else:
                        print("   ⚠️  WARNING - Unexpected response format")
                        all_passed = False
                except json.JSONDecodeError:
                    print(f"   ❌ FAILED - Response is not valid JSON")
                    print(f"   Raw response: {response.text[:500]}")
                    all_passed = False

    except httpx.ConnectError as e:
        print(f"   ❌ FAILED - Connection error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ FAILED - Error: {e}")
        return False

    print()

    # Test 2: List tools
    print("2. Testing 'tools/list' method...")
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(mcp_url, headers=headers, json=tools_request)

            print(f"   Status: {response.status_code}")

            if response.status_code != 200:
                print(f"   ❌ FAILED - Expected 200, got {response.status_code}")
                all_passed = False
            else:
                try:
                    data = response.json()

                    if "result" in data:
                        tools = data.get("result", {}).get("tools", [])
                        print(f"   ✅ PASSED - Found {len(tools)} tools")
                        for tool in tools[:10]:  # Show first 10
                            print(f"      - {tool.get('name', 'unnamed')}")
                        if len(tools) > 10:
                            print(f"      ... and {len(tools) - 10} more")
                    elif "error" in data:
                        print(f"   ❌ FAILED - Server returned error: {data['error']}")
                        all_passed = False
                    else:
                        print("   ⚠️  WARNING - Unexpected response format")
                        print(f"   Response: {json.dumps(data, indent=2)[:500]}")

                except json.JSONDecodeError:
                    print(f"   ❌ FAILED - Response is not valid JSON")
                    all_passed = False

    except Exception as e:
        print(f"   ❌ FAILED - Error: {e}")
        all_passed = False

    print()

    # Test 3: Call a tool (list_projects)
    print("3. Testing 'tools/call' method (chicory_list_projects)...")
    call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "chicory_list_projects",
            "arguments": {}
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(mcp_url, headers=headers, json=call_request)

            print(f"   Status: {response.status_code}")

            if response.status_code != 200:
                print(f"   ❌ FAILED - Expected 200, got {response.status_code}")
                all_passed = False
            else:
                try:
                    data = response.json()

                    if "result" in data:
                        print(f"   ✅ PASSED - Tool executed successfully")
                        result_preview = json.dumps(data.get("result", {}))[:300]
                        print(f"   Result preview: {result_preview}...")
                    elif "error" in data:
                        error = data.get("error", {})
                        # Tool not found is a valid MCP response
                        if error.get("code") == -32601:  # Method not found
                            print(f"   ⚠️  Tool not found (this may be expected)")
                        else:
                            print(f"   ❌ FAILED - Server returned error: {error}")
                            all_passed = False
                    else:
                        print("   ⚠️  WARNING - Unexpected response format")

                except json.JSONDecodeError:
                    print(f"   ❌ FAILED - Response is not valid JSON")
                    all_passed = False

    except Exception as e:
        print(f"   ❌ FAILED - Error: {e}")
        all_passed = False

    print()
    print(f"{'='*60}")
    if all_passed:
        print("✅ All MCP protocol tests PASSED")
    else:
        print("❌ Some MCP protocol tests FAILED")
    print(f"{'='*60}\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test MCP server protocol compliance")
    parser.add_argument("--url", default=os.getenv("CHICORY_MCP_BASE_URL", "http://localhost:3000"),
                        help="MCP server base URL")
    parser.add_argument("--api-key", default=os.getenv("CHICORY_MCP_API_KEY", ""),
                        help="API key for authentication")

    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key required. Set CHICORY_MCP_API_KEY or use --api-key")
        sys.exit(1)

    success = test_mcp_server(args.url, args.api_key)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
