from pathlib import Path
import sys

p = Path("prompts/main.csv")
if not p.exists():
    print("File not found:", p)
    sys.exit(1)

data = p.read_bytes()

needle = b"EX-0049"
idx = data.find(needle)
if idx == -1:
    print("EX-0049 not found in file.")
    sys.exit(2)

start = data.rfind(b"\n", 0, idx)
if start == -1:
    start = 0
else:
    start = start + 1
end = data.find(b"\n", idx)
if end == -1:
    end = len(data) - 1
slice_bytes = data[start:end+1]

print("BYTE OFFSET start,end:", start, end)
print("HEX:")
print(" ".join(f"{b:02X}" for b in slice_bytes))
print("\n--- Decoded views ---\n")

encodings = [
    ("UTF-8", "utf-8"),
    ("CP949", "cp949"),
    ("UTF-16LE", "utf-16le"),
    ("Latin1", "latin-1"),
]
for name, enc in encodings:
    try:
        s = slice_bytes.decode(enc)
    except Exception as e:
        s = f"<decode error: {e}>"
    print(f"{name}:")
    print(s)
    print()

print("--- raw bytes repr (python bytes literal) ---")
repr_bytes = repr(slice_bytes)
if len(repr_bytes) > 1000:
    print(repr_bytes[:1000] + "...(truncated)")
else:
    print(repr_bytes)
