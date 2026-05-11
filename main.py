# main.py — ScopeCreep Phase 1
# SOW Parser v1: extracts project name, in-scope deliverables,
# and out-of-scope items from a scope-of-work document.

# ----- 1. The sample SOW we'll parse -----
# Triple quotes ( """ ) let us write a string that spans many lines.
# Eventually this will be replaced by user input or a pasted contract.

sample_sow = """
Project: Marketing Website Redesign

Deliverables:
- Homepage design and development
- About page
- Contact form with email integration
- Mobile responsive layout
- Basic SEO setup

Excluded:
- Blog functionality
- E-commerce / shopping cart
- Multi-language support
- Custom CMS
"""
# ----- 1.5 Choose: sample SOW or user-pasted SOW -----

print("Press ENTER to use the sample SOW.")
print("Or type 'paste' and press ENTER to paste your own SOW:")
choice = input("> ").strip().lower()

if choice == "paste":
    print("\nPaste your SOW below. When you're finished, type 'END' on a new line and press ENTER:\n")
    user_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        user_lines.append(line)
    sow_text = "\n".join(user_lines)
else:
    print("\nUsing sample SOW.\n")
    sow_text = sample_sow
# ----- 2. Set up the containers we'll fill as we parse -----

project_name = ""        # we'll fill this in when we find a "Project:" line
in_scope = []            # empty list — we'll add deliverables here
out_of_scope = []        # empty list — we'll add excluded items here
current_section = None   # tracks which section we're currently reading
                         # ("in_scope", "out_of_scope", or None)

# ----- 3. Walk through the SOW one line at a time -----

lines = sow_text.split("\n")   # split the multi-line string into a list of lines

for line in lines:
    line = line.strip()          # remove leading/trailing whitespace
    
    if line == "":               # skip blank lines
        continue
    
    line_lower = line.lower()    # lowercase copy for case-insensitive matching
    
    if line_lower.startswith("project:"):
        # Everything after "Project:" is the project name
        project_name = line.split(":", 1)[1].strip()
        current_section = None
    elif line_lower.startswith("deliverables"):
        current_section = "in_scope"
    elif line_lower.startswith("excluded"):
        current_section = "out_of_scope"
    elif line.startswith("-"):
        # It's a bullet item — add it to whichever section we're in
        item = line.lstrip("-").strip()
        if current_section == "in_scope":
            in_scope.append(item)
        elif current_section == "out_of_scope":
            out_of_scope.append(item)

# ----- 4. Print the result -----

print("=" * 50)
print("PARSED SCOPE OF WORK")
print("=" * 50)
print(f"Project: {project_name}")
print()
print("IN SCOPE:")
for item in in_scope:
    print(f"  - {item}")
print()
print("OUT OF SCOPE:")
for item in out_of_scope:
    print(f"  - {item}")
print("=" * 50)
# ------ 5. Scope Checker -------
# Takes incoming client requests, check them against parsed scope using keyword matching.
# Flag anything that looks like out-of-scope work.

print()
print("=" * 50)
print("SCOPE CHECKER")
print("=" * 50)
print("Type a client request to check. Type 'quit' to exit.\n")

while True:
    request = input("Client request: ").strip()
    if request == "":
        continue
    if request.lower() == "quit":
        print("Done checking. Bye!")
        break

    request_lower = request.lower()

# Check against out-of-scope items first (the riskiest)
    matched_excluded = []
    for excluded_item in out_of_scope:
        for word in excluded_item.lower().split():
            if len(word) > 3 and word in request_lower:
                matched_excluded.append(excluded_item)   # was: matched_excluded = excluded_item
                break # stop checking other words in this item — already added

 # Check against in-scope items
    matched_in_scope = []
    for in_scope_item in in_scope:
        for word in in_scope_item.lower().split():
            if len(word) > 3 and word in request_lower:
                matched_in_scope.append(in_scope_item)
                break
    
    # Decide and print the verdict
    # Decide and print the verdict
    print()
    if matched_excluded:
        print("[!] POTENTIAL SCOPE CREEP")
        print(f"    Matches {len(matched_excluded)} excluded item(s):")
        for item in matched_excluded:
            print(f"      - {item}")
        print("    Recommendation: send a change order before doing this work.")
    elif matched_in_scope:
        print("[OK] LIKELY IN SCOPE")
        print(f"     Matches {len(matched_in_scope)} deliverable(s):")
        for item in matched_in_scope:
            print(f"      - {item}")
    else:
        print("[?] UNCLEAR")
        print("    No strong match. Ask the client to clarify, then update the SOW.")
    print()

