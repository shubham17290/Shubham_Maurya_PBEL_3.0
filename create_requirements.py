#!/usr/bin/env python3
# Create requirements.txt with UTF-8 encoding (no BOM)

import os

req_path = r'd:\002 IBM\'S internship\02 Projects\Fake_News_Detection_Using_Machine_learning\requirements.txt'

# The dependencies from the original UTF-16 file
dependencies = """Flask==3.0.3
gunicorn==22.0.0
numpy<2.0.0
pandas==2.2.2
scikit-learn==1.3.2
scipy==1.11.4
Cython==0.29.36
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
print("File content:")
print("="*50)
with open(req_path, 'r', encoding='utf-8') as f:
    print(f.read())
