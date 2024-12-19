import os

def create_document_directory(parent_dir, sub_dir_name):
    """Create a new document directory under the parent directory."""
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    
    sub_dir_path = os.path.join(parent_dir, sub_dir_name)
    if not os.path.exists(sub_dir_path):
        os.makedirs(sub_dir_path)
        print(f"Created new document directory: {sub_dir_path}")
    else:
        print(f"Document directory already exists: {sub_dir_path}")

    return sub_dir_path

def update_gitignore_for_parent(parent_dir):
    """Add the parent directory to .gitignore if it's not already listed."""
    gitignore_path = ".gitignore"
    with open(gitignore_path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        if f"{parent_dir}/" not in lines:
            f.write(f"{parent_dir}/\n")
            print(f"Added {parent_dir}/ to .gitignore")