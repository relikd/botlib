# How-to web scraping

Use the `playground.py` for quick testing.
Initially, you have to set `cache_only=False` or otherwise no data is downloaded.
After the first download, re-enable `cache_only` so you don't have to download the data over and over again.
Also, when you feel ready, uncomment the `break` statement to see if it works for all entries.

## Finding a proper `select`

The hardest part is getting all regex matches right.
Open the browser devtools and choose the element picker.
Hover over the first element / row of the data you'd like to retrieve.
Pick whatever tag or class seems apropriate, also look at neighboring tags.
The `select` must match all entries but no unnecessary ones.
Although you can always filter unnecessary ones later...

## Finding the regex

The matches for the individual data fields are tricky too.
Select and right-click on the element you picked above.
Important: Either edit or copy as raw HTML.
The devtools will omit whitespace and display `'` as `"`, so you have to make sure you know what you are trying to match.

Now begins the playing around part.
The regex will match the first occurrence, so if there are two anchor tags and you need the second one, you have to get creative.
For example, this is the case in the craigslist example.
Here I can match the second anchor because it is contained in a `h3` heading.

Try to match as compact as possible, this makes it more robust against source code changes.
For example, use `<a [^>]*>` to match an opening anchor with arbitrary attributes.
Some sites will put the `href` immediatelly after `<a`, other somewhere in between.
Be creative.
Use `[\s\S]*?` to match anything (instead of just `.`), including whitespace and newlines.
And finally, have at least one matching group (`()`).
Note: whitespace will be stripped from the matching group.
