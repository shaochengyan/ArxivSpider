git add ./arxiv_spider.py config.yaml readme.md requirements.txt run_push_git.bat readme.assets
git commit -m "upload"
git branch -M main
git remote add origin https://github.com/shaochengyan/ArxivSpider.git
git push -u origin main