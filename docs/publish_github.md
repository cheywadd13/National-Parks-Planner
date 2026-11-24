# Publish the solo project repository

The supplied URL identifies the student's GitHub **profile**, not an existing
National Parks repository. Public repositories checked on November 21 did not
include this project. Local Git history is prepared; no remote publication is
claimed until an authenticated push succeeds.

Suggested repository name: `national-parks-travel-planner`. Create an empty
repository under `cheywadd13` using the intended visibility. Do not initialize
it with another README if pushing the prepared local history.

From the final project directory, after creating that repository:

```powershell
git remote add origin https://github.com/cheywadd13/national-parks-travel-planner.git
git push -u origin main
```

If an origin already exists, inspect `git remote -v` before changing it. Use
normal GitHub authentication; never insert a token into the remote URL or
commit a secret. Check that the remote contains README, `app.py`, source modules,
tests, SQL, source provenance, report PDF and screenshots. Confirm the instructor
can access a private repository if private visibility is chosen.

The meaningful phase commits were created during this finishing work. They
are not presented as a reconstruction of earlier semester activity. This is
a solo submission: do not invent additional contributors or commit authors.
