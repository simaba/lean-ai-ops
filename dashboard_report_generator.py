class DashboardReportGenerator:
    def __init__(self, control_plan, improvement_results):
        self.control_plan = control_plan
        self.improvement_results = improvement_results

    def generate_summary(self):
        # Generate project status summary
        summary = {
            'project_status': 'Improvement ongoing',
            'total_actions': len(self.control_plan['metrics']),
            'total_owners': len(self.control_plan['owners']),
            'actions_reviewed': sum([1 for action in self.control_plan['metrics'] if action['metric']])
        }
        return summary

    def action_tracker(self):
        # Generate action tracker for improvements
        action_tracker = [
            {'action': action['action'], 'status': 'Ongoing', 'owner': action['owner']}
            for action in self.control_plan['metrics']
        ]
        return action_tracker

    def before_after_comparison(self):
        # Generate before and after comparison
        before_after = [
            {'metric': action['metric'],
             'before': 'Baseline Value', 'after': 'Improved Value'}
            for action in self.control_plan['metrics']
        ]
        return before_after

    def generate_report(self):
        summary = self.generate_summary()
        action_tracker = self.action_tracker()
        before_after = self.before_after_comparison()

        report = {
            'summary': summary,
            'action_tracker': action_tracker,
            'before_after_comparison': before_after
        }
        return report