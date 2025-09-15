import requests
from bs4 import BeautifulSoup
import subprocess
import platform
from pathlib import Path
from typing import Optional


def scrape_and_download_image(base_url: str, user: str) -> Optional[str]:
    """
    Scrape a user profile page and download the first image found.
    
    Args:
        base_url: Base URL of the website
        user: Username to scrape
        
    Returns:
        Filename of downloaded image, or None if failed
    """
    try:
        # Construct URL and fetch page
        page_url = f"{base_url}/profiles/{user}"
        response = requests.get(page_url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find first image
        images = soup.find_all("img")
        if not images:
            print(f"No images found on {page_url}")
            return None
            
        first_img = images[0]
        img_src = first_img.get("src")
        if not img_src:
            print("Image source not found")
            return None
            
        # Construct full image URL
        img_url = f"{base_url}{img_src}"
        img_name = Path(img_url).name
        
        print(f"Downloading image: {img_name}")
        
        # Download image
        img_response = requests.get(img_url, timeout=10)
        img_response.raise_for_status()
        
        # Save image
        with open(img_name, "wb") as f:
            f.write(img_response.content)
            
        print(f"Image saved as: {img_name}")
        return img_name
        
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def open_image(filename: str) -> None:
    """Open image file using system default application."""
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            subprocess.run(['open', filename], check=True)
        elif system == "Windows":
            subprocess.run(['start', filename], shell=True, check=True)
        elif system == "Linux":
            subprocess.run(['xdg-open', filename], check=True)
        else:
            print(f"Unknown OS: {system}. Please open {filename} manually.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to open image: {e}")


def main():
    """Main function to orchestrate the scraping and downloading process."""
    base_url = "http://olympus.realpython.org"
    user_to_find = "dionysus"
    
    # Download image
    img_filename = scrape_and_download_image(base_url, user_to_find)
    
    if img_filename:
        # Open the downloaded image
        open_image(img_filename)
    else:
        print("Failed to download image")


if __name__ == "__main__":
    main()
