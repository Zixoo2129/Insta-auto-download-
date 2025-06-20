import random
import re

# List of viral hashtags (you can customize this list)
VIRAL_HASHTAGS = [
    "#trending", "#news", "#breaking", "#viral", "#reels", "#dailyupdate", "#instadaily",
    "#foryou", "#explorepage", "#todaynews", "#india", "#update", "#instanews",
    "#headlines", "#currentaffairs", "#factcheck", "#exclusive", "#latestnews",
    "#worldnews", "#localnews", "#community", "#publicsafety", "#government"
]

def format_caption(original_caption, old_username="@mewsinsta", new_username="@newswire.in"):
    # Replace the primary old username with the new one (case-insensitive)
    modified_caption = re.sub(re.escape(old_username), new_username, original_caption, flags=re.IGNORECASE)

    # Also replace @india.news.24x7 with new_username if it exists
    modified_caption = re.sub(re.escape("@india.news.24x7"), new_username, modified_caption, flags=re.IGNORECASE)

    modified_caption = modified_caption.strip() # Remove leading/trailing whitespace
    
    # Add 10 random viral hashtags
    # Ensure there are enough unique hashtags to pick 10
    num_tags_to_add = min(10, len(VIRAL_HASHTAGS))
    selected_tags = random.sample(VIRAL_HASHTAGS, num_tags_to_add)
    hashtags = " ".join(selected_tags)
    
    final_caption = f"{modified_caption}\n\n{hashtags}" # Added an extra newline for better spacing
    return final_caption
