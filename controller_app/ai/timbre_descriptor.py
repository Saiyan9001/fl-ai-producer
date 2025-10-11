"""
Timbre descriptor module for extracting audio features
and providing parameter suggestions for synthesizers
"""
import logging
import numpy as np
import librosa
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParameterSuggestion:
    """Class for storing synthesizer parameter suggestions"""
    param_name: str
    value: float
    min_value: float = 0.0
    max_value: float = 1.0
    confidence: float = 1.0
    description: str = ""


class TimbreDescriptor:
    """
    A class for analyzing audio timbre and suggesting synthesizer parameters
    based on spectral and temporal features.
    """
    
    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        """
        Initialize the timbre descriptor.
        
        Args:
            sample_rate: Audio sample rate
            hop_length: Hop length for feature extraction
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
    
    def extract_features(self, audio: np.ndarray) -> Dict:
        """
        Extract a comprehensive set of audio features.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Dictionary of extracted features
        """
        logger.info("Extracting timbre features")
        features = {}
        
        # Compute MFCCs
        mfccs = librosa.feature.mfcc(
            y=audio, 
            sr=self.sample_rate, 
            n_mfcc=13,
            hop_length=self.hop_length
        )
        features['mfcc_mean'] = np.mean(mfccs, axis=1)
        features['mfcc_std'] = np.std(mfccs, axis=1)
        
        # Compute spectral features
        spectral_centroid = librosa.feature.spectral_centroid(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )[0]
        features['spectral_centroid_mean'] = np.mean(spectral_centroid)
        features['spectral_centroid_std'] = np.std(spectral_centroid)
        
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )[0]
        features['spectral_bandwidth_mean'] = np.mean(spectral_bandwidth)
        
        spectral_flatness = librosa.feature.spectral_flatness(
            y=audio,
            hop_length=self.hop_length
        )[0]
        features['spectral_flatness_mean'] = np.mean(spectral_flatness)
        
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )[0]
        features['spectral_rolloff_mean'] = np.mean(spectral_rolloff)
        
        # Compute zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(
            y=audio,
            hop_length=self.hop_length
        )[0]
        features['zcr_mean'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)
        
        # Compute temporal features
        rms = librosa.feature.rms(
            y=audio,
            hop_length=self.hop_length
        )[0]
        features['rms_mean'] = np.mean(rms)
        features['rms_std'] = np.std(rms)
        
        # Compute attack time (time to reach 95% of the maximum amplitude)
        if len(audio) > 0:
            envelope = np.abs(audio)
            max_amp = np.max(envelope)
            if max_amp > 0:
                # Find the first time the signal reaches 95% of max amplitude
                threshold = 0.95 * max_amp
                for i, amp in enumerate(envelope):
                    if amp >= threshold:
                        features['attack_time'] = i / self.sample_rate
                        break
                else:
                    features['attack_time'] = 0.0
            else:
                features['attack_time'] = 0.0
        else:
            features['attack_time'] = 0.0
        
        # Compute harmonic and percussive components
        harmonic, percussive = librosa.effects.hpss(audio)
        features['harmonic_ratio'] = np.sum(harmonic**2) / (np.sum(audio**2) + 1e-10)
        features['percussive_ratio'] = np.sum(percussive**2) / (np.sum(audio**2) + 1e-10)
        
        return features
    
    def generate_parameter_suggestions(self, features: Dict, synth_type: str = "subtractive") -> List[ParameterSuggestion]:
        """
        Generate synthesizer parameter suggestions based on extracted features.
        
        Args:
            features: Dictionary of extracted audio features
            synth_type: Type of synthesizer ('subtractive', 'fm', 'wavetable', etc.)
            
        Returns:
            List of parameter suggestions
        """
        logger.info(f"Generating parameter suggestions for {synth_type} synthesizer")
        suggestions = []
        
        # Normalize centroid to 0-1 range (assuming 0-10000Hz range)
        normalized_centroid = min(1.0, features['spectral_centroid_mean'] / 10000.0)
        
        # Filter cutoff based on spectral centroid
        suggestions.append(ParameterSuggestion(
            param_name="filter_cutoff",
            value=normalized_centroid,
            description=f"Filter cutoff based on spectral centroid: {features['spectral_centroid_mean']:.2f}Hz"
        ))
        
        # Filter resonance based on spectral bandwidth
        # Normalize bandwidth (0-5000Hz range)
        normalized_bandwidth = min(1.0, features['spectral_bandwidth_mean'] / 5000.0)
        suggestions.append(ParameterSuggestion(
            param_name="filter_resonance",
            value=1.0 - normalized_bandwidth,  # Inverse relationship
            description=f"Filter resonance based on spectral bandwidth: {features['spectral_bandwidth_mean']:.2f}Hz"
        ))
        
        # Attack time based on the measured attack
        if 'attack_time' in features:
            # Normalize attack time (0-2 seconds range)
            normalized_attack = min(1.0, features['attack_time'] / 2.0)
            suggestions.append(ParameterSuggestion(
                param_name="env_attack",
                value=normalized_attack,
                description=f"Envelope attack based on measured attack time: {features['attack_time']:.3f}s"
            ))
        
        # Envelope sustain based on RMS
        normalized_rms = min(1.0, features['rms_mean'] * 5)  # Scale RMS to 0-1
        suggestions.append(ParameterSuggestion(
            param_name="env_sustain",
            value=normalized_rms,
            description=f"Envelope sustain based on RMS: {features['rms_mean']:.3f}"
        ))
        
        # Oscillator waveform suggestion based on harmonic content
        harmonic_ratio = features['harmonic_ratio']
        spectral_flatness = features['spectral_flatness_mean']
        
        # Determine oscillator type based on harmonic content and spectral flatness
        if harmonic_ratio > 0.8 and spectral_flatness < 0.1:
            # Harmonically rich, not noisy: likely a saw or square wave
            if features['zcr_mean'] > 0.4:
                osc_type = "square"
                osc_value = 0.75
            else:
                osc_type = "saw"
                osc_value = 0.5
        elif harmonic_ratio > 0.6:
            # Moderately harmonic: could be a triangle or blend
            osc_type = "triangle"
            osc_value = 0.25
        else:
            # More noise-like or sinusoidal
            if spectral_flatness > 0.2:
                osc_type = "noise"
                osc_value = 1.0
            else:
                osc_type = "sine"
                osc_value = 0.0
        
        suggestions.append(ParameterSuggestion(
            param_name="osc_waveform",
            value=osc_value,
            description=f"Oscillator waveform suggestion: {osc_type} (based on harmonic ratio: {harmonic_ratio:.2f})"
        ))
        
        # For subtractive synthesis
        if synth_type == "subtractive":
            # Oscillator detune based on spectral spread
            suggestions.append(ParameterSuggestion(
                param_name="osc_detune",
                value=min(1.0, features['spectral_bandwidth_mean'] / 2000.0),
                description="Oscillator detune based on spectral bandwidth"
            ))
        
        # For FM synthesis
        elif synth_type == "fm":
            # Modulation index based on spectral complexity
            mod_index = min(1.0, features['spectral_bandwidth_mean'] / 3000.0)
            suggestions.append(ParameterSuggestion(
                param_name="fm_mod_index",
                value=mod_index,
                description="FM modulation index based on spectral bandwidth"
            ))
            
            # Modulator frequency ratio based on spectral features
            if features['spectral_centroid_mean'] > 3000:
                mod_ratio = 2.0  # Higher ratios for brighter sounds
                mod_ratio_value = 0.8
            elif features['spectral_centroid_mean'] > 1000:
                mod_ratio = 1.0
                mod_ratio_value = 0.5
            else:
                mod_ratio = 0.5  # Lower ratios for darker sounds
                mod_ratio_value = 0.2
                
            suggestions.append(ParameterSuggestion(
                param_name="fm_mod_ratio",
                value=mod_ratio_value,
                description=f"FM modulator ratio suggestion: {mod_ratio}"
            ))
        
        # Add reverb suggestion based on spectral features
        if features['spectral_flatness_mean'] < 0.1 and features['harmonic_ratio'] > 0.7:
            # Harmonically rich sounds often benefit from less reverb
            reverb_amount = 0.2
        else:
            # More noise-like or percussive sounds can use more reverb
            reverb_amount = 0.4
            
        suggestions.append(ParameterSuggestion(
            param_name="reverb_amount",
            value=reverb_amount,
            description=f"Reverb amount suggestion: {reverb_amount:.2f}"
        ))
        
        return suggestions
    
    def analyze(self, audio_path: str, synth_type: str = "subtractive") -> Dict:
        """
        Complete analysis pipeline from audio to synthesizer parameter suggestions.
        
        Args:
            audio_path: Path to audio file
            synth_type: Type of synthesizer
            
        Returns:
            Dictionary with features and parameter suggestions
        """
        logger.info(f"Analyzing timbre of {audio_path}")
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Extract features
        features = self.extract_features(audio)
        
        # Generate parameter suggestions
        suggestions = self.generate_parameter_suggestions(features, synth_type)
        
        return {
            "features": features,
            "suggestions": suggestions
        }

    def map_to_plugin_params(self, 
                             suggestions: List[ParameterSuggestion], 
                             plugin_params: Dict[str, Dict]) -> Dict[str, float]:
        """
        Map generic parameter suggestions to specific plugin parameters.
        
        Args:
            suggestions: List of parameter suggestions
            plugin_params: Dictionary of plugin parameters with name, index, min, max
            
        Returns:
            Dictionary mapping plugin parameter indices to suggested values
        """
        logger.info("Mapping suggestions to plugin parameters")
        
        # Create a dictionary to store the mapped plugin parameter values
        mapped_params = {}
        
        # Define a mapping of common parameter name patterns to our suggestion keys
        param_mapping = {
            # Filter parameters
            "cutoff": "filter_cutoff",
            "freq": "filter_cutoff",
            "filter": "filter_cutoff",
            "resonance": "filter_resonance",
            "q": "filter_resonance",
            "res": "filter_resonance",
            
            # Envelope parameters
            "attack": "env_attack",
            "sustain": "env_sustain",
            "decay": "env_decay",
            "release": "env_release",
            
            # Oscillator parameters
            "wave": "osc_waveform",
            "waveform": "osc_waveform",
            "shape": "osc_waveform",
            "detune": "osc_detune",
            
            # FM parameters
            "mod": "fm_mod_index",
            "ratio": "fm_mod_ratio",
            
            # Effects parameters
            "reverb": "reverb_amount",
            "delay": "delay_amount"
        }
        
        # Create a dictionary of our suggestions for easy lookup
        suggestion_dict = {s.param_name: s for s in suggestions}
        
        # Iterate through plugin parameters and find matches with our suggestions
        for param_name, param_info in plugin_params.items():
            param_name_lower = param_name.lower()
            
            # Try to find a matching parameter
            for pattern, suggestion_key in param_mapping.items():
                if pattern in param_name_lower and suggestion_key in suggestion_dict:
                    # We found a matching parameter
                    suggestion = suggestion_dict[suggestion_key]
                    
                    # Scale the suggestion value to the plugin parameter range
                    plugin_min = param_info.get('min', 0.0)
                    plugin_max = param_info.get('max', 1.0)
                    
                    # Scale from suggestion range (0-1) to plugin range
                    scaled_value = plugin_min + suggestion.value * (plugin_max - plugin_min)
                    
                    # Store the mapped parameter
                    mapped_params[param_info['index']] = scaled_value
                    
                    logger.info(f"Mapped {suggestion_key} to plugin parameter '{param_name}' with value {scaled_value}")
                    break
        
        return mapped_params