# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Myzel** is a custom AWS Infrastructure as Code (IAC) framework in Python. It allows you to define AWS resources as Python classes, automatically detect differences between desired and actual state, and apply changes with dry-run support.

**Key Philosophy**: Diff-based deployments with YAML state management - similar to Terraform but as a lightweight Python framework.

## High-Level Architecture

```
┌─────────────────────────────────────────────┐
│         Application (AwsApp)                │
│  - Defines desired resources                │
│  - Contains list of Resource objects        │
└──────────────────────┬──────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         v                           v
┌──────────────────────┐  ┌─────────────────────┐
│  Resources           │  │  deploy() Function  │
│  (S3, Lambda, etc)   │  │  - Orchestrator     │
│  - Implement         │  │  - Returns results  │
│    get_resource_id() │  └──────┬──────────────┘
│  - CRUD methods      │         │
└─────────┬────────────┘         │
          │                      │
          ├──────────────────────┤
          v                      v
      ┌─────────────────────────────────┐
      │    DiffEngine                   │
      │  - Compares desired vs actual   │
      │  - Identifies CREATE/UPDATE/DELETE
      └──────────┬──────────────────────┘
               │
               v
      ┌─────────────────────────────────┐
      │    StateManager                 │
      │  - Reads/writes YAML config     │
      │  - Manages version increments   │
      │  - Persists resource metadata   │
      └─────────────────────────────────┘
               │
               v
      ┌─────────────────────────────────┐
      │    config/app_<name>.yaml       │
      │  - Current state of resources   │
      │  - AWS IDs and metadata         │
      │  - Version tracking             │
      └─────────────────────────────────┘
```

### Key Concepts

1. **Resources as Classes**: AWS resources (S3, Lambda, etc.) are defined as Python classes inheriting from `Resources` base class
2. **Fachliche Resource IDs**: Each resource provides a meaningful ID (e.g., bucket name) not just indices
3. **State Files**: YAML files store current deployment state: `config/app_<app_name>.yaml`
4. **Diff Detection**: Compares desired state (Python objects) with actual state (AWS) to generate diffs
5. **Dry-Run Support**: Preview changes without executing them


# !!! IMPORTANT: Dont Write Docu and Tests !!!
