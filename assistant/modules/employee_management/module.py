from assistant.core import Module, ModuleConfig

class EmployeeManagementModule(Module):
    @property
    def name(self) -> str:
        return "employee_management"
    @property
    def display_name(self) -> str:
        return "Employee Management"
    @property
    def description(self) -> str:
        return "Multi-user task management and approvals"
    @property
    def version(self) -> str:
        return "1.0.0"
    @property
    def owner_only(self) -> bool:
        return True
