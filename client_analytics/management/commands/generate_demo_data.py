"""
Django management command to generate demo Excel files
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
import numpy as np
import os


class Command(BaseCommand):
    help = 'Generate demo Excel files for testing'

    def handle(self, *args, **options):
        demo_dir = os.path.join(
            settings.BASE_DIR,
            'client_analytics',
            'demo_data'
        )
        
        # Create demo_data directory if it doesn't exist
        os.makedirs(demo_dir, exist_ok=True)
        
        # Generate Demo 1
        self.stdout.write('Generating demo_clients_1.xlsx...')
        df1 = self.generate_demo_1()
        demo1_path = os.path.join(demo_dir, 'demo_clients_1.xlsx')
        df1.to_excel(demo1_path, index=False)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {demo1_path}'))
        
        # Generate Demo 2
        self.stdout.write('Generating demo_clients_2.xlsx...')
        df2 = self.generate_demo_2()
        demo2_path = os.path.join(demo_dir, 'demo_clients_2.xlsx')
        df2.to_excel(demo2_path, index=False)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {demo2_path}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Demo datasets generated successfully!'))

    def generate_demo_1(self):
        """Generate demo dataset 1 - Basic client data"""
        np.random.seed(42)
        n = 500
        
        data = {
            'customer_id': [f'CUST{i:04d}' for i in range(1, n + 1)],
            'age': np.random.randint(18, 75, n),
            'gender': np.random.choice(['M', 'F', 'Other'], n, p=[0.48, 0.48, 0.04]),
            'country': np.random.choice(
                ['France', 'Belgium', 'Germany', 'UK', 'Spain', 'Italy'],
                n,
                p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05]
            ),
            'total_spent': np.random.exponential(1000, n).round(2),
            'num_orders': np.random.poisson(5, n),
            'avg_order_value': np.random.normal(200, 50, n).round(2),
            'days_since_last_order': np.random.randint(0, 365, n),
            'account_age_days': np.random.randint(30, 1825, n),
            'loyalty_points': np.random.randint(0, 5000, n),
            'category': np.random.choice(
                ['Electronics', 'Clothing', 'Home', 'Books', 'Sports'],
                n,
                p=[0.3, 0.25, 0.2, 0.15, 0.1]
            ),
            'churn': np.random.choice([0, 1], n, p=[0.75, 0.25])
        }
        
        df = pd.DataFrame(data)
        
        # Make total_spent positive and correlated with num_orders
        df['total_spent'] = np.abs(df['total_spent'])
        df['total_spent'] = df['total_spent'] + df['num_orders'] * 50
        
        # Make avg_order_value positive
        df['avg_order_value'] = np.abs(df['avg_order_value']) + 50
        
        return df

    def generate_demo_2(self):
        """Generate demo dataset 2 - Purchase behavior data"""
        np.random.seed(123)
        n = 400
        
        data = {
            'customer_id': [f'USR{i:05d}' for i in range(1, n + 1)],
            'age': np.random.randint(20, 70, n),
            'income': np.random.normal(50000, 20000, n).round(0),
            'family_size': np.random.randint(1, 7, n),
            'education': np.random.choice(
                ['High School', 'Bachelor', 'Master', 'PhD'],
                n,
                p=[0.3, 0.4, 0.2, 0.1]
            ),
            'marital_status': np.random.choice(
                ['Single', 'Married', 'Divorced', 'Widowed'],
                n,
                p=[0.35, 0.45, 0.15, 0.05]
            ),
            'purchase_frequency': np.random.randint(1, 50, n),
            'avg_basket_size': np.random.normal(5, 2, n).round(0),
            'online_purchases': np.random.randint(0, 30, n),
            'store_purchases': np.random.randint(0, 30, n),
            'discount_usage': np.random.uniform(0, 1, n).round(2),
            'satisfaction_score': np.random.randint(1, 11, n),
            'region': np.random.choice(
                ['North', 'South', 'East', 'West', 'Central'],
                n,
                p=[0.2, 0.2, 0.25, 0.2, 0.15]
            ),
            'customer_segment': np.random.choice(
                ['Premium', 'Standard', 'Basic'],
                n,
                p=[0.2, 0.5, 0.3]
            )
        }
        
        df = pd.DataFrame(data)
        
        # Make income positive
        df['income'] = np.abs(df['income']) + 20000
        
        # Make avg_basket_size positive
        df['avg_basket_size'] = np.abs(df['avg_basket_size']) + 1
        
        # Add some missing values for realism
        missing_mask = np.random.random(n) < 0.05
        df.loc[missing_mask, 'satisfaction_score'] = np.nan
        
        return df
