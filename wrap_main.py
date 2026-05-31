with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where session state init starts
start_idx = -1
for i, line in enumerate(lines):
    if line.startswith("# Session State Init"):
        start_idx = i - 1
        break

# Find where helper functions start
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("def _render_multi_comparison") or line.startswith("def _render_comparison_result"):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx]
    new_lines.append("\ndef main():\n")
    
    for line in lines[start_idx:end_idx]:
        if line == "\n":
            new_lines.append(line)
        else:
            new_lines.append("    " + line)
            
    new_lines.extend(lines[end_idx:])
    
    new_lines.append("\nif __name__ == '__main__':\n    main()\n")
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
