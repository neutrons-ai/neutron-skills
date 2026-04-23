# Project Overview

We are building a repository of curated agent skills for neutron scattering.

## Project Name
neutron-skills


## Description
The purpose of this project is to develop a python package that provides agent skills following the standard specifications.
That package can then be imported and used by other agents. It needs to includes a registry/lookup for the agents to use.
The neutron skills will be organized for curation, in a directory structure. For instance, there will be a general scattering folder, a diffraction folder, etc...

Fro reference, follow the skills specifications:
https://agentskills.io/specification

And how they should be used:
https://agentskills.io/client-implementation/adding-skills-support


## Example Usage
<!-- How would someone use your package? Show a simple example. -->

```python
# Example:
from neutron-skills import retrieve

skills, tools = retrieve("We are writing a scan script to acquire data on the EQSANS instrument at SNS.")

# Insert skills in prompt
# Pass tools to LLM call

```


## Dependencies
- For CLI, use click.

