# Troubleshooting Guide

### Common Issues

1. **No PR Comments Posted**
   - Ensure `CHICORY_API_TOKEN` and `CHICORY_AGENT_ID` are set in repo secrets.

2. **Analysis Timeout**
   - The agent waits up to 5 minutes. Check agent logs in Chicory dashboard.

3. **Diff File Empty**
   - Confirm your `path_filter` matches (`models/**/*.sql` vs `src/`).

---

Feel free to reach out to Chicory Team for any issues.
