# Python Refactoring Guidelines

## Purpose

Provide reusable guidance for safely refactoring Python backend applications while preserving behavior and maintaining testable architectural boundaries.

## Requirements

### Requirement: Skill identity and refactoring reference
The package SHALL identify `python-backend` as a reusable Skill that guides an executing agent, and SHALL provide a valid dedicated reference for Python backend refactoring.

#### Scenario: Agent loads refactoring guidance
- **WHEN** an agent activates the Python backend Skill for an existing-backend refactoring
- **THEN** the Skill points to an existing Python refactoring reference and does not require an autonomous Agent implementation

### Requirement: Target project organization
The refactoring guidance SHALL recommend application code under `app/` and tests under `app/tests/` for new projects, while allowing an equivalent existing project layout, including a top-level `tests/` directory, to remain when moving files would add risk without improving boundaries.

#### Scenario: Existing project already uses target layout
- **WHEN** application and test files are located under `app/` and `app/tests/`
- **THEN** refactoring keeps production code and tests within those directories

#### Scenario: Existing project uses equivalent layout
- **WHEN** a project has a coherent equivalent layout outside `app/` and `app/tests/`
- **THEN** the agent may preserve that layout and SHALL document the equivalence rather than perform an unnecessary move

### Requirement: Proportional class abstractions
The refactoring guidance SHALL organize cohesive methods and responsibilities in appropriate classes and SHALL introduce abstract contracts for repositories, services, controllers, handlers, or equivalent replaceable boundaries only when a concrete architectural or testability problem justifies them.

#### Scenario: Boundary needs substitution
- **WHEN** a component must be replaced, isolated, or independently tested across a meaningful boundary
- **THEN** the agent defines an abstraction owned by the appropriate module

#### Scenario: Trivial behavior has no boundary need
- **WHEN** a function or module has cohesive trivial behavior and no substitution or isolation need
- **THEN** the agent does not add a wrapper class or interface solely for convention

### Requirement: Abstract class convention
Architecturally justified nominal class abstractions SHALL use `ABC` and `abstractmethod` from Python's `abc` module. Structural ports MAY use `Protocol` when duck typing is sufficient and no nominal inheritance or shared abstract behavior is required. Concrete implementations SHALL implement every abstract method with valid Python syntax and naming. Normative examples SHALL respect the Skill's declared Python compatibility range or explicitly declare a newer version requirement.

#### Scenario: Repository contract is introduced
- **WHEN** a repository abstraction is architecturally justified
- **THEN** it inherits from `ABC`, declares its contract with `@abstractmethod`, and has a concrete implementation that fulfills the contract

#### Scenario: Structural port is introduced
- **WHEN** a port needs only structural typing
- **THEN** the agent may define it with `Protocol` instead of `ABC`

#### Scenario: Compatible type syntax is selected
- **WHEN** a refactoring example targets the declared Python 3.8+ compatibility
- **THEN** its type syntax is valid for Python 3.8 or the example explicitly requires a newer version

### Requirement: Constructor dependency injection
Refactored components SHALL receive their dependencies through constructors, and application, domain, controller, and handler code SHALL NOT use a Service Locator or resolve dependencies from a container.

#### Scenario: Component receives a dependency
- **WHEN** a service, controller, handler, or equivalent component depends on another component
- **THEN** the dependency is explicit in its constructor and stored for use

#### Scenario: Runtime component needs resolution
- **WHEN** dependencies must be assembled for execution
- **THEN** resolution occurs in the composition root rather than inside business or boundary code

### Requirement: Punq registration
When a project uses Punq or explicitly adopts it, the composition root SHALL register each required abstraction with its concrete implementation and SHALL keep container configuration outside business logic.

#### Scenario: Punq is already present
- **WHEN** refactoring a project that uses Punq to assemble dependencies
- **THEN** the agent updates registrations for affected abstractions and concrete implementations in the composition root

#### Scenario: Project has no container
- **WHEN** a project does not use Punq and no container is required by the requested change
- **THEN** the agent does not introduce Punq solely to satisfy this guidance

### Requirement: Unit-testable boundaries
Refactoring SHALL preserve or improve unit-test isolation by designing replaceable boundaries that can use mocks, stubs, and fakes, preferring the simplest test double that clearly expresses the test.

#### Scenario: External dependency is isolated
- **WHEN** a unit test exercises logic that depends on persistence or an external service
- **THEN** the test supplies an appropriate mock, stub, or fake without requiring the real external system

### Requirement: Coordinated refactoring updates
When affected by a boundary move, the agent SHALL update imports, application composition, Punq configuration, Alembic configuration or migrations, and tests as one coherent change.

#### Scenario: Persistence boundary moves
- **WHEN** repository or database integration code is relocated
- **THEN** imports, composition, relevant Alembic configuration or migrations, and persistence tests remain consistent

### Requirement: Behavioral compatibility
Refactoring SHALL preserve existing API contracts, response and error behavior, transaction semantics, database behavior, and other observable runtime behavior unless the user explicitly requests a functional change.

#### Scenario: API boundary is refactored
- **WHEN** controller, handler, service, or application composition code changes
- **THEN** existing API inputs, outputs, status and error behavior remain compatible

#### Scenario: Database boundary is refactored
- **WHEN** persistence code or its surrounding composition changes
- **THEN** existing schema behavior, data semantics, transaction boundaries, and migration expectations remain compatible

### Requirement: Incremental verification
The executing agent SHALL validate refactoring incrementally using existing project tooling and tests at the affected architectural boundaries, and SHALL report unresolved trade-offs or test gaps. Tool recommendations for new projects SHALL NOT be interpreted as mandatory replacements for configured tooling in existing projects.

#### Scenario: Boundary refactoring is complete
- **WHEN** implementation changes are finished
- **THEN** targeted tests and existing type-check, lint, migration, or architecture checks are run where available, without adding unrelated tooling

#### Scenario: Compatibility risk exists
- **WHEN** direct replacement could break existing callers
- **THEN** the agent uses characterization or contract tests and a compatibility adapter or staged migration where appropriate

#### Scenario: Existing tooling is configured
- **WHEN** an existing project uses a configured test or lint runner
- **THEN** the agent uses that runner and does not add a replacement solely because a different tool is recommended for new projects

### Requirement: Copy-safe refactoring examples
Refactoring guidance SHALL make required imports, symbols, constructor dependencies, return behavior, and compatibility assumptions clear in copyable examples, or SHALL label abbreviated snippets as illustrative.

#### Scenario: Boundary is refactored
- **WHEN** an agent uses a refactoring example for a repository, service, controller, or handler boundary
- **THEN** the example identifies its dependencies and return behavior without presenting undefined symbols as a complete implementation

#### Scenario: Python 3.8 example is copied
- **WHEN** an agent copies a normative refactoring example
- **THEN** its type syntax is valid for Python 3.8+ or the example clearly states its version gate
