Verify that the AIPEA implementation matches SPECIFICATION.md.

Steps:
1. Read `SPECIFICATION.md` to extract:
   - All defined modules and their responsibilities
   - All public classes/functions specified
   - All environment variables specified
   - All compliance modes specified
   - All processing tiers and query types
2. Read `src/aipea/__init__.py` to get the actual public API (`__all__`)
3. For each module in the spec, read the corresponding source file and verify:
   - All specified classes/functions exist
   - All specified parameters are present
   - Return types match specification
4. Check for implementation drift:
   - Features in code but NOT in spec (undocumented)
   - Features in spec but NOT in code (unimplemented)
5. Report as a table: Feature | Spec Status | Code Status | Match?
6. Flag any critical mismatches that need attention
