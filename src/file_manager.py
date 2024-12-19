from termcolor import colored
import os

def create_document_directory(parent_dir, sub_dir_name):
    """Create a new document directory under the parent directory."""
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    
    sub_dir_path = os.path.join(parent_dir, sub_dir_name)
    if not os.path.exists(sub_dir_path):
        os.makedirs(sub_dir_path)
        print(colored(f"Created new document directory: {sub_dir_path}", "green"))
    else:
        print(colored(f"Document directory already exists: {sub_dir_path}", "yellow"))

    return sub_dir_path

def update_gitignore_for_parent(parent_dir):
    """Add the parent directory to .gitignore if it's not already listed."""
    gitignore_path = ".gitignore"
    with open(gitignore_path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        if f"{parent_dir}/\n" not in lines:
            f.write(f"{parent_dir}/\n")
            print(colored(f"Added {parent_dir}/ to .gitignore", "green"))