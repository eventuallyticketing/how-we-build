# How Eventually gets built

The post about how Kelsey and Zack build Eventually, and every version of it.

`post.md` is the one source. Each day it changes becomes a step on the slider at build.eventuallyticketing.com, labelled with the first line of that day's last commit.

## Updating the post

1. Edit `post.md`.
2. Commit with a first line that says what changed, for example `Add a section on support`. A second paragraph in the commit message becomes the day's summary.
3. Push to `main`. GitHub Pages rebuilds the site.

To preview locally: `python3 build.py`, then open `_site/index.html`.
