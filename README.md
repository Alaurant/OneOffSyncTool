# OneOffSyncTool
A tool for Jenkins RPU to do one-off back-fill from GitHub to Yaml

## Current Progress
### Sync Logic
The tool merges developer lists from both GitHub and YAML sources. 
For instance:
- If a YAML file lists "Alice" and "Bob" while GitHub has "Bob" and "Claire", the resulting YAML will include "Alice", "Bob", and "Claire".
```
developers:
  - ldap: "Bob"
    github: "Bob"
  - ldap: "Alice"
    github: ""
  - ldap: ""
    github: "Claire"
```
- But if a user both in yaml and GitHub with different username, it would be two records.
```
developers:
  - ldap: "Bob_in_ladp"
    github: ""
  - ldap: ""
    github: "Bob_in_github"
```
- If you have suggestions for improving this merging strategy or if adjustments are needed to better meet our sync goals, please provide your feedback. 

### Challenges Identified
- **Untracked Teams in GitHub**: Approximately 500 teams identified on GitHub do not have corresponding YAML files within their repositories. This issue suggests these teams cannot be managed or accessed via YAML, which might hinder synchronization and management efforts.
- **YAML Files Without GitHub Records**: Around 100 YAML files have developer entries that are not recorded on GitHub. Although this might seem minor, it is crucial for ensuring all team data is synchronized accurately across platforms.
- For detailed results, please refer to the files located in `other/*.txt`.
  

### Testing and Validation
- **Unit Tests**: Initial unit tests have been conducted to ensure the tool's functionality.
- **Virtual Organization Testing**: Further tests have been performed within our virtual organization. For detailed examples and results, please refer to the files located in `example/*.yml`.
  
## Requirements for Completion
To finalize and fully deploy this tool, the following are required:
1. **Extended Permissions**:
   - I currently possess read permissions at the organization level but require read access to individual repositories to utilize [GitHub's List Repository Teams API](https://docs.github.com/en/rest/repos/repos#list-repository-teams).
2. **Clarification of Special Teams**:
   - Identification of special teams: The correlation between teams defined in GitHub and those listed in `teams/*.yml` needs clarification. Assistance from anyone who is familiar with jenkinsci GitHub team is necessary to update and verify these team name.
   - For example: change `name: "ux"` to `name: "SIG: UX"` in `teams/ux.yml`
- **Challenges with Multiple YAML Files for a Single Repository:**
  Managing multiple YAML files corresponding to a single repository introduces synchronization challenges. Specifically, if a new member is added to one YAML file but not others, there's a risk that this member could be inadvertently removed during synchronization when another YAML file is updated and submitted to GitHub. 

## Next Steps
- **Enhanced Testing:**
  Continue extensive testing to ensure robust performance and identify any potential issues that may not have surfaced during initial trials.

- **Subproject Integration:**
  Consider using subprojects or similar approaches that allow for back-fill operations without interrupting the main Repository Permissions Updater (RPU) processes. 

Your insights and contributions are invaluable as we aim to refine and deploy the OneOffSyncTool effectively. Thank you for your guidance and support.

- **Explanation on Non-usage of Maven:**
  Initially, I implemented this tool using Maven, investing effort to ensure everything was set up correctly. However, despite many attempts, the `snakeyaml` dependency exhibited limitations with preserving comments and anchors in YAML files. Consequently, I had to switch to Python.

