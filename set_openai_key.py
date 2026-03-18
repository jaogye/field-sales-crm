import subprocess

# Key split into short segments to avoid terminal wrapping issues
key = (
    "sk-proj-PGQ7W8U1WoXeMgHjPDne5LPLwewjE2Hwkx7EUMtO"
    "hSK1SAwiEl1FzY2sZ9OXE6JAo3x7PbFTC-"
    "T3BlbkFJ53WYXW5kcjN1M4O1JGKq"
    "sZSmrjx3Z-sOis4qW9nolmoH3ss1UXvjcpAmZbTaSfS4gFelION78A"
)

print(f"Key length: {len(key)}")
print(f"Has spaces: {' ' in key}")
print(f"Has newlines: {chr(10) in key}")
print(f"Key: {key[:20]}...{key[-10:]}")
print()

result = subprocess.run(
    ["flyctl", "secrets", "set", f"OPENAI_API_KEY={key}", "-a", "field-sales-crm"],
    capture_output=False
)
print(f"Exit code: {result.returncode}")
