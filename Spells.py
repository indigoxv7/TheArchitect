from enum import Enum

class SpellComponent(Enum):
    VERBAL = 'verbal'
    SOMATIC = 'somatic'
    MATERIAL = 'material'


class Spell:
    def __init__(self, name, level, power, affinity, casting_time, range, components, duration, description, higher_level=None):
        self.name = name
        self.level = level
        self.power = power
        self.affinity = affinity
        self.casting_time = casting_time
        self.range = range
        self.components = components  # Components should be a dict with keys: 'verbal', 'somatic', 'material'
        self.duration = duration
        self.description = description
        self.higher_level = higher_level

    def cast_spell(self, caster, target):
        """
        Perform the actions required to cast the spell.
        This is a basic implementation, and should be expanded based on the game's mechanics.
        """
        # Check if the caster has the necessary components and spell slots
        if not self.has_required_components(caster):
            return f"{caster.name} does not have the required components to cast {self.name}."

        result = f"{caster.name} casts {self.name} on {target.name}."

        # Apply spell effects based on the spell description
        result += f"\n{self.description}"

        if self.higher_level:
            result += f"\nAt higher levels: {self.higher_level}"

        return result

    def has_required_components(self, caster):
        """
        Check if the caster has the required components to cast the spell.
        This function should be expanded to include checks for material components, etc.
        """
        # Example check for components
        if self.components.get('verbal') and not caster.has_verbal_component():
            return False
        if self.components.get('somatic') and not caster.has_somatic_component():
            return False
        if self.components.get('material') and not caster.has_material_component(self.components['material']):
            return False

        return True

    def __str__(self):
        components = ', '.join([
            'V' if self.components.get('verbal') else '',
            'S' if self.components.get('somatic') else '',
            f"M ({self.components['material']})" if self.components.get('material') else ''
        ]).strip(', ')

        spell_info = (f"Name: {self.name}\n"
                      f"Level: {self.level}\n"
                      f"affinity: {self.affinity}\n"
                      f"Casting Time: {self.casting_time}\n"
                      f"Range: {self.range}\n"
                      f"Components: {components}\n"
                      f"Duration: {self.duration}\n"
                      f"Description: {self.description}")

        if self.higher_level:
            spell_info += f"\nAt Higher Levels: {self.higher_level}"

        return spell_info