"""
Tests for User Prompt Templates

Tests that templates produce valid structures and parameter ranges.
No network required - all tests are purely local.
"""
import pytest
from controller_app.ai.templates.user_prompts import (
    design_synth_prompt,
    make_melody_prompt,
    recreate_instrument_prompt,
    remix_pattern_prompt,
    get_all_templates,
    get_template_names
)


class TestDesignSynthTemplate:
    """Tests for synth design template."""
    
    def test_basic_synth_design(self):
        """Test basic synth design template."""
        result = design_synth_prompt(
            style_tags="dark pluck, detuned, short decay",
            channel_ref="0"
        )
        
        assert "prompt" in result
        assert "category" in result
        assert "tool_calls_expected" in result
        assert "parameters" in result
        
        assert result["category"] == "sound_design"
        assert "list_state" in result["tool_calls_expected"]
        assert "get_params" in result["tool_calls_expected"]
        assert "set_param" in result["tool_calls_expected"]
        
        assert "dark pluck, detuned, short decay" in result["prompt"]
        assert "Channel 0" in result["prompt"]
    
    def test_synth_design_no_test_note(self):
        """Test synth design without test note."""
        result = design_synth_prompt(
            style_tags="bright pad",
            channel_ref="2",
            add_test_note=False
        )
        
        assert "set_note_batch" not in result["prompt"]
        assert result["parameters"]["add_test_note"] is False
    
    def test_synth_design_with_test_note(self):
        """Test synth design with test note."""
        result = design_synth_prompt(
            style_tags="bass",
            add_test_note=True
        )
        
        assert "set_note_batch" in result["prompt"]
        assert "pitch 60" in result["prompt"]
        assert result["parameters"]["add_test_note"] is True


class TestMakeMelodyTemplate:
    """Tests for melody generation template."""
    
    def test_basic_melody(self):
        """Test basic melody generation."""
        result = make_melody_prompt(
            key="C",
            scale="major",
            mood="happy",
            channel_ref="0"
        )
        
        assert "prompt" in result
        assert result["category"] == "melody_generation"
        assert "list_state" in result["tool_calls_expected"]
        assert "set_note_batch" in result["tool_calls_expected"]
        
        assert "C major" in result["prompt"]
        assert "happy" in result["prompt"]
        assert result["parameters"]["root_note"] == 60
    
    def test_melody_different_keys(self):
        """Test melody with different keys."""
        test_cases = [
            ("C", 60),
            ("D", 62),
            ("E", 64),
            ("F#", 66),
            ("Bb", 70)
        ]
        
        for key, expected_root in test_cases:
            result = make_melody_prompt(key=key, scale="major")
            assert result["parameters"]["root_note"] == expected_root
    
    def test_melody_different_moods(self):
        """Test melody with different moods."""
        moods = ["happy", "sad", "energetic", "melancholy", "custom"]
        
        for mood in moods:
            result = make_melody_prompt(mood=mood)
            assert mood in result["prompt"]
            assert result["parameters"]["mood"] == mood
    
    def test_melody_with_tempo(self):
        """Test melody with specific tempo."""
        result = make_melody_prompt(tempo=120)
        
        assert "120 BPM" in result["prompt"]
        assert result["parameters"]["tempo"] == 120
    
    def test_melody_num_bars(self):
        """Test melody with different bar counts."""
        result = make_melody_prompt(num_bars=8)
        
        assert "8 bars" in result["prompt"]
        assert result["parameters"]["num_bars"] == 8


class TestRecreateInstrumentTemplate:
    """Tests for instrument recreation template."""
    
    def test_basic_instrument_recreation(self):
        """Test basic instrument recreation."""
        timbre = {
            "brightness": 0.7,
            "noisiness": 0.2,
            "attack_time": 0.1,
            "sustain_level": 0.8
        }
        
        result = recreate_instrument_prompt(timbre, target_channel="1")
        
        assert "prompt" in result
        assert result["category"] == "instrument_recreation"
        assert "list_state" in result["tool_calls_expected"]
        assert "get_params" in result["tool_calls_expected"]
        assert "set_param" in result["tool_calls_expected"]
        
        assert "0.70" in result["prompt"] or "0.7" in result["prompt"]
        assert result["parameters"]["brightness"] == 0.7
    
    def test_instrument_recreation_parameter_ranges(self):
        """Test that parameter values are in valid ranges."""
        timbre = {
            "brightness": 0.5,
            "noisiness": 0.3,
            "attack_time": 0.15,
            "sustain_level": 0.6
        }
        
        result = recreate_instrument_prompt(timbre)
        params = result["parameters"]
        
        # All values should be between 0.0 and 1.0
        assert 0.0 <= params["brightness"] <= 1.0
        assert 0.0 <= params["noisiness"] <= 1.0
        assert 0.0 <= params["attack_time"] <= 1.0
        assert 0.0 <= params["sustain_level"] <= 1.0
    
    def test_instrument_recreation_missing_keys(self):
        """Test instrument recreation with missing analysis keys."""
        # Should use defaults
        timbre = {"brightness": 0.8}
        
        result = recreate_instrument_prompt(timbre)
        params = result["parameters"]
        
        assert params["brightness"] == 0.8
        # Should have defaults for missing keys
        assert "noisiness" in params
        assert "attack_time" in params
        assert "sustain_level" in params


class TestRemixPatternTemplate:
    """Tests for pattern remix template."""
    
    def test_basic_remix(self):
        """Test basic pattern remix."""
        result = remix_pattern_prompt(
            transformation="humanize",
            channel_ref="0"
        )
        
        assert "prompt" in result
        assert result["category"] == "pattern_remix"
        assert "list_state" in result["tool_calls_expected"]
        assert "set_note_batch" in result["tool_calls_expected"]
        
        assert "humanize" in result["prompt"]
    
    def test_all_transformation_types(self):
        """Test all transformation types."""
        transformations = ["humanize", "invert", "reverse", "change_rhythm", "transpose"]
        
        for trans in transformations:
            result = remix_pattern_prompt(transformation=trans)
            assert trans in result["prompt"]
            assert result["parameters"]["transformation"] == trans
    
    def test_remix_with_selection_range(self):
        """Test remix with selection range."""
        result = remix_pattern_prompt(
            transformation="invert",
            selection_range=(0, 16)
        )
        
        assert "from beat 0 to 16" in result["prompt"]
        assert result["parameters"]["selection_range"] == (0, 16)
    
    def test_remix_without_selection_range(self):
        """Test remix without selection range."""
        result = remix_pattern_prompt(transformation="reverse")
        
        assert result["parameters"]["selection_range"] is None


class TestTemplateRegistry:
    """Tests for template registry functions."""
    
    def test_get_all_templates(self):
        """Test getting all templates."""
        templates = get_all_templates()
        
        assert isinstance(templates, dict)
        assert "design_synth" in templates
        assert "make_melody" in templates
        assert "recreate_instrument" in templates
        assert "remix_pattern" in templates
        
        # All values should be callable
        for name, func in templates.items():
            assert callable(func)
    
    def test_get_template_names(self):
        """Test getting template names."""
        names = get_template_names()
        
        assert isinstance(names, list)
        assert "design_synth" in names
        assert "make_melody" in names
        assert "recreate_instrument" in names
        assert "remix_pattern" in names
        assert len(names) == 4


class TestTemplateValidation:
    """Tests for validating template outputs."""
    
    def test_all_templates_have_required_fields(self):
        """Test that all templates produce required fields."""
        templates = get_all_templates()
        
        for name, func in templates.items():
            # Call with minimal args
            if name == "design_synth":
                result = func(style_tags="test")
            elif name == "make_melody":
                result = func()
            elif name == "recreate_instrument":
                result = func(timbre_analysis={})
            elif name == "remix_pattern":
                result = func(transformation="humanize")
            else:
                continue
            
            # Check required fields
            assert "prompt" in result, f"{name} missing 'prompt'"
            assert "category" in result, f"{name} missing 'category'"
            assert "tool_calls_expected" in result, f"{name} missing 'tool_calls_expected'"
            assert "parameters" in result, f"{name} missing 'parameters'"
            
            # Check types
            assert isinstance(result["prompt"], str)
            assert isinstance(result["category"], str)
            assert isinstance(result["tool_calls_expected"], list)
            assert isinstance(result["parameters"], dict)
    
    def test_no_network_required(self):
        """Test that templates don't require network access."""
        # All templates should work offline
        result1 = design_synth_prompt("test")
        result2 = make_melody_prompt()
        result3 = recreate_instrument_prompt({})
        result4 = remix_pattern_prompt("humanize")
        
        # If we got here without errors, no network was needed
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result4 is not None
    
    def test_midi_note_ranges(self):
        """Test that MIDI note values are in valid range."""
        # Test melody template
        for key in ["C", "D", "E", "F", "G", "A", "B"]:
            result = make_melody_prompt(key=key)
            root = result["parameters"]["root_note"]
            assert 0 <= root <= 127, f"Root note {root} for key {key} out of range"
    
    def test_normalized_parameter_values(self):
        """Test that normalized parameters are in 0-1 range."""
        timbre = {
            "brightness": 0.5,
            "noisiness": 0.3,
            "attack_time": 0.2,
            "sustain_level": 0.7
        }
        
        result = recreate_instrument_prompt(timbre)
        
        # Check all normalized values are in range
        for key, value in result["parameters"].items():
            if isinstance(value, float) and key != "target_channel":
                assert 0.0 <= value <= 1.0, f"Parameter {key}={value} out of range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
