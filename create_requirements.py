#!/usr/bin/env python3
# Create requirements.txt with UTF-8 encoding (no BOM)
# Optimized for Vercel deployment - minimal dependencies only

import os

req_path = 'requirements.txt'

# Optimized dependencies for Vercel serverless deployment
# Only includes essential packages needed for the API
dependencies = """Flask==3.0.3
scikit-learn==1.3.2
numpy<2.0.0
joblib==1.4.2
"""

# Write with UTF-8 encoding, no BOM
with open(req_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(dependencies)

print(f"Created {req_path}")
print(f"File size: {os.path.getsize(req_path)} bytes")

# Verify the file
with open(req_path, 'rb') as f:
    first_bytes = f.read(10)
    print(f"\nFirst 10 bytes (hex): {first_bytes.hex()}")
    print(f"First 10 bytes (repr): {repr(first_bytes)}")
    
    # Check for BOM
    if first_bytes.startswith(b'\xef\xbb\xbf'):
        print("❌ WARNING: UTF-8 BOM detected!")
    elif first_bytes.startswith(b'\xff\xfe') or first_bytes.startswith(b'\xfe\xff'):
        print("❌ WARNING: UTF-16 BOM detected!")
    else:
        print("✓ No BOM detected - clean UTF-8")
    
    # Check first character
    f.seek(0)
    first_char = f.read(1).decode('utf-8')
    print(f"\nFirst character: {repr(first_char)}")
    print(f"Is alphanumeric: {first_char.isalnum()}")
    
    if first_char.isalnum():
        print("✓ First character is alphanumeric - READY FOR VERCEL!")
    else:
        print(f"❌ First character is NOT alphanumeric!")

# Display the file content
print("\n" + "="*50)
print("Optimized dependencies for Vercel:")
print("="*50)
with open(req_path, 'r', encoding='utf-8') as f:
    print(f.read())

print("\n📦 Dependencies breakdown:")
print("  Flask==3.0.3       - Web framework (required)")
print("  scikit-learn==1.3.2 - Model unpickling (required)")
print("  numpy<2.0.0        - Required by scikit-learn")
print("  joblib==1.4.2      - Model loading (required)")
print("\n💾 Total estimated size: ~63 MB (Vercel limit: 500 MB)")
print("✅ Optimized for Vercel serverless deployment!")
