import requests
import json
import time
import random
import os
import subprocess
import shutil
import socket

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
    })
    return session

def search_github(query, max_pages=20):
    base_url = "https://github.com/search"
    repositories = set()
    total_requests = 0
    start_time = time.time()
    session = create_session()

    print(f"Starting search for query: '{query}'")
    print(f"Maximum pages to search: {max_pages}")

    for page in range(1, max_pages + 1):
        params = {
            'q': query,
            'type': 'repositories',
            'p': page
        }
        
        retry_count = 0
        while True:
            try:
                print(f"\nPreparing to fetch page {page}...")
                delay = random.uniform(10, 15)
                print(f"Waiting for {delay:.2f} seconds before making the request...")
                time.sleep(delay)
                
                print(f"Fetching page {page}...")
                response = session.get(base_url, params=params, timeout=30)
                total_requests += 1
                
                print(f"Response received for page {page}")
                print(f"Status code: {response.status_code}")
                
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count > 12:  # Max retries (up to 120 seconds wait)
                        print("Max retries reached. Moving to next page.")
                        break
                    wait_time = min(10 * retry_count, 120)
                    print(f"Rate limited. Waiting for {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    print(f"Unexpected status code. Response content:")
                    print(response.text[:500])  # Print first 500 characters
                    break
                
                data = json.loads(response.text)
                results = data['payload']['results']
                
                print(f"Found {len(results)} repositories on this page")
                
                new_repos = set()
                for result in results:
                    hl_name = result['hl_name']
                    # Remove <em> tags from hl_name
                    clean_name = hl_name.replace('<em>', '').replace('</em>', '')
                    repo_url = f"https://github.com/{clean_name}"
                    if repo_url not in repositories:
                        new_repos.add(repo_url)
                        repositories.add(repo_url)
                
                print(f"Added {len(new_repos)} new repositories")
                print(f"Total unique repositories: {len(repositories)}")
                
                if len(results) == 0:
                    print("No new repositories found on this page. Stopping search.")
                    return list(repositories)
                
                break  # Successful request, move to next page
                
            except requests.Timeout:
                print(f"Request timed out for page {page}")
                break
            except requests.RequestException as e:
                print(f"An error occurred while fetching page {page}: {e}")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                print(f"Error details: {str(e)}")
                break
        
        print(f"Completed processing for page {page}")
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nSearch completed.")
    print(f"Total time taken: {duration:.2f} seconds")
    print(f"Total requests made: {total_requests}")
    print(f"Total unique repositories found: {len(repositories)}")
    
    return list(repositories)

def save_to_file(repositories, filename):
    with open(filename, 'w') as f:
        for repo in repositories:
            f.write(f"{repo}\n")
    print(f"Saved {len(repositories)} repositories to {filename}")

def run_git_command(command, retry_count=10, wait_time=10):
    for attempt in range(retry_count):
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Command failed (Attempt {attempt + 1}/{retry_count}): {e}")
            print(f"Error output: {e.stderr}")
            if "Could not resolve host" in e.stderr:
                print("DNS resolution error. Checking internet connection...")
                if not check_internet_connection():
                    print("No internet connection. Waiting before retry...")
                    time.sleep(wait_time)
                    continue
            if attempt < retry_count - 1:
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Command failed after {retry_count} attempts.")
                return False
    return False

def check_internet_connection(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def clone_or_update_repo(repo_url, base_folder):
    owner, repo_name = repo_url.split('/')[-2:]
    repo_path = os.path.join(base_folder, f"{owner}_{repo_name}")
    
    if os.path.exists(repo_path):
        print(f"Updating existing repository: {owner}/{repo_name}")
        command = ['git', '-C', repo_path, 'pull']
        if run_git_command(command):
            print(f"Successfully updated {owner}/{repo_name}")
        else:
            print(f"Failed to update {owner}/{repo_name}")
    else:
        print(f"Cloning new repository: {owner}/{repo_name}")
        command = ['git', 'clone', repo_url, repo_path]
        if run_git_command(command):
            print(f"Successfully cloned {owner}/{repo_name}")
        else:
            print(f"Failed to clone {owner}/{repo_name}")

def copy_bcheck_files(source_folder, destination_folder):
    print(f"\nCopying .bcheck files from {source_folder} to {destination_folder}")
    os.makedirs(destination_folder, exist_ok=True)
    
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.bcheck'):
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_folder)
                owner_repo = os.path.dirname(relative_path)
                dest_filename = f"{owner_repo.replace(os.path.sep, '_')}_{file}"
                dest_path = os.path.join(destination_folder, dest_filename)
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(dest_path):
                    base, ext = os.path.splitext(dest_filename)
                    dest_filename = f"{base}_{counter}{ext}"
                    dest_path = os.path.join(destination_folder, dest_filename)
                    counter += 1
                
                shutil.copy2(source_path, dest_path)
                #print(f"Copied: {source_path} -> {dest_path}")

if __name__ == "__main__":
    query = ".bcheck"
    output_file = "bcheck_repositories.txt"
    clone_folder = "bcheck_repos"  # Folder to clone repositories into
    bcheck_files_folder = "all_bcheck_files"  # Folder to store all .bcheck files
    
    print("=== GitHub Repository Search ===")
    repositories = search_github(query)
    
    if repositories:
        print("\nSaving results to file...")
        save_to_file(repositories, output_file)
        
        print("\nCloning or updating repositories...")
        os.makedirs(clone_folder, exist_ok=True)
        for repo in repositories:
            clone_or_update_repo(repo, clone_folder)
        
        print("\nCopying .bcheck files to a single folder...")
        copy_bcheck_files(clone_folder, bcheck_files_folder)
    else:
        print("No repositories found. No file will be saved and no repositories will be cloned.")
    
    print("Script execution completed.")