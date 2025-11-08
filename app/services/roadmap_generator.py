from typing import Dict, List
from datetime import date, timedelta
import math

class RoadmapGenerator:
    """
    Generate personalized day-by-day placement preparation roadmap
    Based on: Impact Score = Company Frequency × Topic Difficulty × Weakness Score
    """
    
    def __init__(self):
        self.frequency_weights = {
            'very_high': 10,
            'high': 7,
            'medium': 5,
            'low': 3
        }
        
        self.difficulty_weights = {
            'easy': 1,
            'medium': 2,
            'hard': 3
        }
    
    def generate_roadmap(
        self,
        company_questions: Dict,
        interview_date: date,
        hours_per_day: float,
        round_structure: List[Dict]
    ) -> Dict:
        """
        Generate complete day-by-day roadmap
        """
        
        days_available = (interview_date - date.today()).days
        if days_available <= 0:
            raise ValueError("Interview date must be in the future")
        
        print(f"\n{'='*60}")
        print(f"🗺️  Generating Roadmap")
        print(f"   Days available: {days_available}")
        print(f"   Hours per day: {hours_per_day}")
        print(f"{'='*60}")
        
        # Calculate questions per day
        daily_dsa_count = min(
            math.floor(hours_per_day * 1.2),
            8  # comfortable max
        )
        
        # Prioritize topics by impact score
        prioritized_topics = self._prioritize_topics(
            company_questions['topics']
        )
        
        # Distribute topics across days
        daily_plan = self._distribute_topics(
            prioritized_topics,
            days_available,
            daily_dsa_count,
            round_structure
        )
        
        # Add side tasks
        roadmap = self._add_side_tasks(
            daily_plan,
            round_structure,
            company_questions.get('system_design', []),
            company_questions.get('behavioral_focus', [])
        )
        
        # Calculate statistics
        stats = self._calculate_stats(roadmap, hours_per_day)
        
        return {
            "roadmap": roadmap,
            "statistics": stats,
            "daily_dsa_count": daily_dsa_count
        }
    
    def _prioritize_topics(self, topics: Dict) -> List[Dict]:
        """
        Calculate impact score and prioritize topics
        Impact = Frequency Weight × Avg Difficulty × Weakness (default 1)
        """
        prioritized = []
        
        for topic_name, topic_data in topics.items():
            frequency = topic_data.get('frequency', 'medium')
            questions = topic_data.get('questions', [])
            
            # Calculate impact score
            freq_weight = self.frequency_weights.get(frequency, 5)
            
            # Assume medium difficulty if not specified
            difficulty_score = 2  # medium default
            
            # Weakness score (1 = new topic, could be adjusted based on user history)
            weakness_score = 1
            
            impact_score = freq_weight * difficulty_score * weakness_score
            
            prioritized.append({
                'name': topic_name,
                'questions': questions,
                'frequency': frequency,
                'recommended_hours': topic_data.get('recommended_hours', 5),
                'impact_score': impact_score,
                'question_count': len(questions)
            })
        
        # Sort by impact score (descending)
        prioritized.sort(key=lambda x: x['impact_score'], reverse=True)
        
        print("   Topic Priority:")
        for idx, topic in enumerate(prioritized[:5]):
            print(f"     {idx+1}. {topic['name']} (score: {topic['impact_score']})")
        
        return prioritized
    
    def _distribute_topics(
        self,
        topics: List[Dict],
        days_available: int,
        daily_dsa_count: int,
        round_structure: List[Dict]
    ) -> List[Dict]:
        """
        Distribute topics across available days
        """
        daily_plan = []
        current_topic_idx = 0
        questions_done_in_topic = 0
        
        for day in range(1, days_available + 1):
            if current_topic_idx >= len(topics):
                current_topic_idx = 0  # Cycle back for revision
            
            current_topic = topics[current_topic_idx]
            
            # Get questions for today
            available_questions = current_topic['questions']
            questions_for_today = available_questions[
                questions_done_in_topic:questions_done_in_topic + daily_dsa_count
            ]
            
            if len(questions_for_today) == 0:
                # Move to next topic
                current_topic_idx += 1
                questions_done_in_topic = 0
                if current_topic_idx < len(topics):
                    current_topic = topics[current_topic_idx]
                    questions_for_today = current_topic['questions'][:daily_dsa_count]
            
            daily_plan.append({
                'day': day,
                'date': (date.today() + timedelta(days=day-1)).isoformat(),
                'topic': current_topic['name'],
                'frequency': current_topic['frequency'],
                'dsa_questions': questions_for_today,
                'question_count': len(questions_for_today),
                'side_task': None,  # Will be added later
                'estimated_hours': len(questions_for_today) * 0.5  # 30 min per question
            })
            
            questions_done_in_topic += len(questions_for_today)
            
            # Move to next topic if current is exhausted
            if questions_done_in_topic >= len(current_topic['questions']):
                current_topic_idx += 1
                questions_done_in_topic = 0
        
        return daily_plan
    
    def _add_side_tasks(
        self,
        daily_plan: List[Dict],
        round_structure: List[Dict],
        system_design: List[str],
        behavioral_focus: List[str]
    ) -> List[Dict]:
        """
        Add side tasks (system design, behavioral prep, aptitude)
        """
        
        # Determine what rounds need preparation
        has_system_design = any(r['type'] == 'system_design' for r in round_structure)
        has_aptitude = any(r['type'] == 'aptitude' for r in round_structure)
        has_hr = any(r['type'] == 'hr' for r in round_structure)
        
        system_design_idx = 0
        behavioral_idx = 0
        
        for day_plan in daily_plan:
            day = day_plan['day']
            
            # Day 1: HR prep intro
            if day == 1 and has_hr:
                day_plan['side_task'] = {
                    'type': 'behavioral',
                    'task': 'Write STAR format examples for past experiences'
                }
            
            # Days 2-3: Aptitude (if needed)
            elif day in [2, 3] and has_aptitude:
                day_plan['side_task'] = {
                    'type': 'aptitude',
                    'task': f'Practice aptitude: {"Ratios & Percentages" if day == 2 else "Time & Work problems"}'
                }
            
            # Every 3rd day: System design (if needed)
            elif day % 3 == 0 and has_system_design and system_design_idx < len(system_design):
                day_plan['side_task'] = {
                    'type': 'system_design',
                    'task': f'Study: {system_design[system_design_idx]}'
                }
                system_design_idx += 1
            
            # Every 4th day: Behavioral prep
            elif day % 4 == 0 and behavioral_idx < len(behavioral_focus):
                day_plan['side_task'] = {
                    'type': 'behavioral',
                    'task': f'Prepare examples for: {behavioral_focus[behavioral_idx]}'
                }
                behavioral_idx += 1
            
            # Last 3 days: Mock interviews
            elif day > len(daily_plan) - 3:
                day_plan['side_task'] = {
                    'type': 'mock',
                    'task': f'Mock interview - Round {len(daily_plan) - day + 1}'
                }
        
        return daily_plan
    
    def _calculate_stats(self, roadmap: List[Dict], hours_per_day: float) -> Dict:
        """
        Calculate roadmap statistics
        """
        total_days = len(roadmap)
        total_questions = sum(day['question_count'] for day in roadmap)
        unique_topics = len(set(day['topic'] for day in roadmap))
        total_hours = total_days * hours_per_day
        
        # Count side tasks by type
        side_task_counts = {}
        for day in roadmap:
            if day['side_task']:
                task_type = day['side_task']['type']
                side_task_counts[task_type] = side_task_counts.get(task_type, 0) + 1
        
        return {
            'total_days': total_days,
            'total_questions': total_questions,
            'unique_topics': unique_topics,
            'total_hours': total_hours,
            'avg_questions_per_day': round(total_questions / total_days, 1),
            'side_task_distribution': side_task_counts
        }
