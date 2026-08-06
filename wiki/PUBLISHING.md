# These are the wiki pages, staged

GitHub creates a repository's wiki git repository only after a first page
exists, and the first page can only be made in the web interface. The
overnight session that wrote these pages could not reach a logged-in browser,
so the pages are staged here instead of being faked or skipped.

To publish them, once:

1. Open https://github.com/Oranburg/meturgaman/wiki and click "Create the
   first page". Save it with any content; it will be overwritten.
2. Then run:

```bash
git clone https://github.com/Oranburg/meturgaman.wiki.git /tmp/meturgaman-wiki
cp wiki/*.md /tmp/meturgaman-wiki/
rm /tmp/meturgaman-wiki/PUBLISHING.md
cd /tmp/meturgaman-wiki && git add -A && git commit -m "The wiki, from the staged pages" && git push
```

After that, this directory can be deleted from the repository, or kept as the
wiki's source of record; either works, but pick one so the two copies do not
drift.
