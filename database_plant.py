import os
from datetime import datetime, timezone
from supabase import create_client

class PlantDatabase:
    def __init__(self, supabase_client):
        """Initialize with a Supabase client"""
        self.client = supabase_client

    def get_user_plant(self, user_id):
        """Get a user's plant or return None if not found"""
        try:
            result = self.client.table('user_plants') \
                .select('*') \
                .eq('user_id', user_id) \
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user plant: {str(e)}")
            return None

    def create_user_plant(self, user_id, plant_type='sunflower'):
        """Create a new plant for a user"""
        try:
            plant_data = {
                'user_id': user_id,
                'plant_type': plant_type,
                'growth_stage': 0,
                'water_count': 0,
                'sunlight_level': 50,  # Default starting level
                'fertilizer_level': 50,  # Default starting level
                'last_watered': None,
                'last_sunlight': None,
                'last_fertilizer': None
            }
            
            result = self.client.table('user_plants') \
                .insert(plant_data) \
                .execute()
                
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error creating user plant: {str(e)}")
            return None

    def water_plant(self, user_id, points):
        """Water the user's plant and update growth"""
        try:
            # Get the user's plant
            plant = self.get_user_plant(user_id)
            if not plant:
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate new water count (cap at 100)
            new_water_count = min(plant.get('water_count', 0) + (points // 10), 100)
            
            # Update the plant
            updated_plant = self.client.table('user_plants') \
                .update({
                    'water_count': new_water_count,
                    'last_watered': datetime.now(timezone.utc).isoformat(),
                    'updated_at': 'now()'
                }) \
                .eq('user_id', user_id) \
                .execute()
                
            if not updated_plant.data:
                return False, None, "Failed to update plant"
                
            # Update plant growth based on all factors
            self._update_plant_growth(user_id, updated_plant.data[0]['id'])
                
            return True, updated_plant.data[0], "Plant watered successfully"
            
        except Exception as e:
            print(f"Error in water_plant: {str(e)}")
            return False, None, str(e)

    def give_sunlight(self, user_id, points):
        """Give sunlight to the user's plant"""
        try:
            plant = self.get_user_plant(user_id)
            if not plant:
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate new sunlight level (cap at 100)
            new_sunlight = min(plant.get('sunlight_level', 50) + (points // 5), 100)
            
            # Update the plant
            updated_plant = self.client.table('user_plants') \
                .update({
                    'sunlight_level': new_sunlight,
                    'last_sunlight': datetime.now(timezone.utc).isoformat(),
                    'updated_at': 'now()'
                }) \
                .eq('user_id', user_id) \
                .execute()
                
            if not updated_plant.data:
                return False, None, "Failed to update plant"
                
            # Update plant growth based on all factors
            self._update_plant_growth(user_id, updated_plant.data[0]['id'])
                
            return True, updated_plant.data[0], "Sunlight given to plant"
            
        except Exception as e:
            print(f"Error in give_sunlight: {str(e)}")
            return False, None, str(e)

    def give_fertilizer(self, user_id, points):
        """Give fertilizer to the user's plant"""
        try:
            plant = self.get_user_plant(user_id)
            if not plant:
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate new fertilizer level (cap at 100)
            new_fertilizer = min(plant.get('fertilizer_level', 50) + (points // 2), 100)
            
            # Update the plant
            updated_plant = self.client.table('user_plants') \
                .update({
                    'fertilizer_level': new_fertilizer,
                    'last_fertilizer': datetime.now(timezone.utc).isoformat(),
                    'updated_at': 'now()'
                }) \
                .eq('user_id', user_id) \
                .execute()
                
            if not updated_plant.data:
                return False, None, "Failed to update plant"
                
            # Update plant growth based on all factors
            self._update_plant_growth(user_id, updated_plant.data[0]['id'])
                
            return True, updated_plant.data[0], "Fertilizer given to plant"
            
        except Exception as e:
            print(f"Error in give_fertilizer: {str(e)}")
            return False, None, str(e)

    def _update_plant_growth(self, user_id, plant_id):
        """Update plant growth stage based on all factors"""
        try:
            # Call the database function to update growth
            result = self.client.rpc('update_plant_growth', {
                'p_user_id': user_id,
                'p_plant_id': plant_id
            }).execute()
            
            return result.data
            
        except Exception as e:
            print(f"Error updating plant growth: {str(e)}")
            return None

    def get_plant_stats(self, user_id):
        """Get all plant statistics for a user"""
        try:
            plant = self.get_user_plant(user_id)
            if not plant:
                return None
                
            return {
                'growth_stage': plant.get('growth_stage', 0),
                'water_count': plant.get('water_count', 0),
                'sunlight_level': plant.get('sunlight_level', 50),
                'fertilizer_level': plant.get('fertilizer_level', 50),
                'last_watered': plant.get('last_watered'),
                'last_sunlight': plant.get('last_sunlight'),
                'last_fertilizer': plant.get('last_fertilizer'),
                'plant_type': plant.get('plant_type', 'sunflower')
            }
            
        except Exception as e:
            print(f"Error getting plant stats: {str(e)}")
            return None
