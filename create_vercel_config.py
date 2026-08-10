#!/usr/bin/env python3
"""
Create optimized vercel.json configuration for Vercel deployment.
This script generates a clean, properly formatted vercel.json file.
"""

import json
import os

# Vercel configuration optimized for the Fake News Detection API
vercel_config = {
    "version": 2,
    "builds": [
        {
            "src": "app.py",
            "use": "@vercel/python",
            "config": {
                "maxLambdaSize": "50mb",
                "runtime": "python3.12",
                "memory": 1024,
                "maxDuration": 10,
                "includeFiles": [
                    "model/**/*",
                    "templates/**/*",
                    "static/**/*",
                    "utils/**/*",
                    "routes/**/*",
                    "config.py",
                    "app.py",
                    "requirements.txt"
                ],
                "excludeFiles": [
                    # Virtual environments
                    "**/venv/**",
                    "**/.venv/**",
                    "**/env/**",
                    "**/ENV/**",
                    "**/myenv/**",
                    # Python cache
                    "**/__pycache__/**",
                    # Version control
                    "**/.git/**",
                    # IDE folders
                    "**/.vscode/**",
                    "**/.idea/**",
                    "**/node_modules/**",
                    # Large datasets (51+ MB)
                    "data/**/*.csv",
                    "data/**/*.xlsx",
                    "data/**/*.json",
                    # Development folders
                    "notebooks/**",
                    "assets/**",
                    # Compiled files
                    "**/*.pyc",
                    "**/*.pyo",
                    "**/*.pyd",
                    "**/*.so",
                    "**/*.dll",
                    "**/*.dylib",
                    # Temporary files
                    "**/*.log",
                    "**/*.tmp",
                    "**/*.temp",
                    # OS files
                    "**/.DS_Store",
                    "**/Thumbs.db",
                    # Test files
                    "**/*.test.py",
                    "**/test_*.py",
                    # Coverage reports
                    "**/htmlcov/**",
                    "**/.tox/**",
                    "**/.pytest_cache/**",
                    "**/.coverage",
                    "**/coverage.xml",
                    "**/*.cover",
                    # Build artifacts
                    "**/build/**",
                    "**/dist/**",
                    "**/*.egg-info/**",
                    "**/*.egg",
                    "**/MANIFEST",
                    # Documentation (except README)
                    "docs/**",
                    "**/*.md",
                    "!README.md"
                ]
            }
        }
    ],
    "routes": [
        {
            "src": "/(.*)",
            "dest": "/app.py"
        }
    ],
    "env": {
        "FLASK_ENV": "production"
    },
    "regions": ["iad1"],
    "cleanUrls": True,
    "trailingSlash": False
}

# Write the configuration file with UTF-8 encoding (no BOM)
vercel_json_path = 'vercel.json'
with open(vercel_json_path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(vercel_config, f, indent=2)
    f.write('\n')

print(f"✓ Created {vercel_json_path}")
print(f"✓ File size: {os.path.getsize(vercel_json_path)} bytes")

# Verify the file
with open(vercel_json_path, 'rb') as f:
    first_bytes = f.read(10)
    
    # Check for BOM
    if first_bytes.startswith(b'\xef\xbb\xbf'):
        print("❌ WARNING: UTF-8 BOM detected!")
    else:
        print("✓ No BOM - clean UTF-8")

# Validate JSON
with open(vercel_json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    print("[OK] Valid JSON")
    print(f"[OK] Version: {data['version']}")
    print(f"[OK] Builds: {len(data['builds'])}")
    print(f"[OK] Routes: {len(data['routes'])}")
    print(f"[OK] Exclude patterns: {len(data['builds'][0]['config']['excludeFiles'])}")
    print(f"[OK] Runtime: {data['builds'][0]['config']['runtime']}")
    print(f"[OK] Memory: {data['builds'][0]['config']['memory']}MB")
    print(f"[OK] Max Duration: {data['builds'][0]['config']['maxDuration']}s")

print("\n" + "="*60)
print("Vercel Configuration Summary:")
print("="*60)
print("Entry Point:     app.py")
print("Builder:         @vercel/python")
print("Runtime:         python3.12")
print("Memory:          1024 MB")
print("Max Duration:    10 seconds")
print("Max Lambda:      50 mb")
print("Routes:          All traffic -> /app.py")
print("Clean URLs:      Enabled")
print("Region:          iad1 (US East)")
print("\nExcluded bloat:")
print("  • Virtual environments: ~300+ MB saved")
print("  • Large datasets: ~51 MB saved")
print("  • Python cache, IDE files, tests, docs")
print("\n✅ vercel.json is ready for deployment!")
