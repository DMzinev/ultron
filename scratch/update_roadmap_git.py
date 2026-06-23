import os

def update_file(filepath):
    if not os.path.exists(filepath):
        print(f"[-] File not found: {filepath}")
        return
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Locate the text to remove
    to_remove = """### Git-history bug-fix extraction (`extract_git_history`)
**Confirmed:** the working directory is not a git repository, so this
feature has been returning an empty result on every run — silently, with no
error or warning surfaced to the user. The "increase sensitivity for
historically bug-prone files" behavior it was meant to drive has, in
practice, never activated. Fixing this needs two things: actually running
inside a git repo, and a visible warning when the feature can't find history
to use, so a silent no-op never gets mistaken for a working feature again.
"""
    # Try with different newlines/spaces if match fails
    if to_remove not in content:
        # Standardize newlines
        content_std = content.replace("\r\n", "\n")
        to_remove_std = to_remove.replace("\r\n", "\n")
        if to_remove_std in content_std:
            content = content_std.replace(to_remove_std, "")
        else:
            print(f"[-] Could not find original text in {filepath}")
            return
    else:
        content = content.replace(to_remove, "")

    # 2. Insert under ## ⚠️ Working, not yet validated
    insert_target = "## ⚠️ Working, not yet validated\n"
    new_text = """### Git-history bug-fix extraction (`extract_git_history`)
**Confirmed:** the feature runs and correctly parses commit history. If the repo is missing or contains zero matches, it outputs clear warnings rather than failing silently.

**Gap:** the efficacy of using bug-fix commit frequency to scale static risk warnings is not yet validated against real-world defect density.

"""
    idx = content.find(insert_target)
    if idx != -1:
        insert_pos = idx + len(insert_target)
        # Check if there is an empty line next
        if content[insert_pos] == "\n":
            insert_pos += 1
        content = content[:insert_pos] + new_text + content[insert_pos:]
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Successfully updated {filepath}")
    else:
        print(f"[-] Target section header not found in {filepath}")

update_file("ROADMAP.md")
