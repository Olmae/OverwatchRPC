# Release checks, dynamic catalog and usability

Implement locally in the current native Tk application; preserve the existing work.

1. Test release selection (semantic versions, beta/stable channels, drafts, malformed data).
   Add bounded GitHub requests. Offer the official release page; do not replace running binaries.
2. Test validated catalog refresh and atomic cache writes. Fetch the official Blizzard
   hero roster and OverFast maps in background. Preserve reviewed translations and offline data.
3. Start optional background checks on launch. Keep network work off the UI thread;
   defer update prompts while hidden or while the game runs. Add manual controls.
4. Replace OCR language typing with a localized dropdown. Add bounded interval controls
   and localized hero/map pickers. Keep the profile at the top of Additional.
5. Rewrite README feature and bug-report text to match the implemented behavior.
6. Run focused and full tests, native Windows UI checks, frozen self-tests; rebuild ZIP.
