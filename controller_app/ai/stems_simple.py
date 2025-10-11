"""
Simple audio stem separation using Harmonic-Percussive Source Separation (HPSS)
"""
import os
import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class SimpleStemSeparator:
    """
    A lightweight stem separator using librosa's HPSS algorithm
    to separate harmonic and percussive components.
    """
    
    def __init__(self, 
                 sample_rate: int = 22050, 
                 hop_length: int = 512,
                 margin_harmonic: float = 3.0,
                 margin_percussive: float = 3.0):
        """
        Initialize the stem separator.
        
        Args:
            sample_rate: Audio sample rate
            hop_length: Hop length for STFT
            margin_harmonic: Margin for harmonic extraction
            margin_percussive: Margin for percussive extraction
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.margin_harmonic = margin_harmonic
        self.margin_percussive = margin_percussive
        
    def load_audio(self, audio_path: str) -> np.ndarray:
        """
        Load audio file and resample if necessary.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Audio data as numpy array
        """
        logger.info(f"Loading audio from {audio_path}")
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        return y
    
    def separate_harmonic_percussive(self, audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Separate audio into harmonic and percussive components using HPSS.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Tuple of (harmonic, percussive) components
        """
        logger.info("Separating harmonic and percussive components")
        
        # Apply HPSS
        harmonic, percussive = librosa.effects.hpss(
            audio, 
            margin=(self.margin_harmonic, self.margin_percussive),
            hop_length=self.hop_length
        )
        
        return harmonic, percussive
    
    def separate_bass(self, harmonic: np.ndarray, cutoff: int = 250) -> Tuple[np.ndarray, np.ndarray]:
        """
        Separate bass from harmonic component using a low-pass filter.
        
        Args:
            harmonic: Harmonic component of audio
            cutoff: Cutoff frequency in Hz
            
        Returns:
            Tuple of (bass, midrange_harmonic) components
        """
        logger.info(f"Separating bass with cutoff at {cutoff}Hz")
        
        # Apply low-pass filter to isolate bass
        bass = librosa.effects.low_pass_filter(harmonic, sr=self.sample_rate, cutoff=cutoff)
        
        # Subtract bass from harmonic to get mid-range
        midrange_harmonic = harmonic - bass
        
        return bass, midrange_harmonic
    
    def separate_stems(self, audio_path: str, include_bass: bool = True) -> Dict[str, np.ndarray]:
        """
        Separate audio file into stems.
        
        Args:
            audio_path: Path to audio file
            include_bass: Whether to separate bass from harmonic content
            
        Returns:
            Dictionary of stem names to audio data
        """
        logger.info(f"Separating stems for {audio_path}")
        
        # Load audio
        audio = self.load_audio(audio_path)
        
        # Separate harmonic and percussive components
        harmonic, percussive = self.separate_harmonic_percussive(audio)
        
        stems = {
            "harmonic": harmonic,
            "percussive": percussive
        }
        
        # Optionally separate bass from harmonic content
        if include_bass:
            bass, midrange = self.separate_bass(harmonic)
            stems["bass"] = bass
            stems["midrange"] = midrange
        
        return stems
    
    def export_stems(self, 
                     stems: Dict[str, np.ndarray], 
                     output_dir: str, 
                     base_filename: str) -> Dict[str, str]:
        """
        Export separated stems to audio files.
        
        Args:
            stems: Dictionary of stem names to audio data
            output_dir: Directory to save stems
            base_filename: Base filename for stems
            
        Returns:
            Dictionary of stem names to file paths
        """
        logger.info(f"Exporting stems to {output_dir}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Export each stem
        stem_paths = {}
        for name, audio in stems.items():
            # Create output path
            output_path = os.path.join(output_dir, f"{base_filename}_{name}.wav")
            
            # Save audio file
            sf.write(output_path, audio, self.sample_rate)
            
            stem_paths[name] = output_path
        
        return stem_paths
    
    def process(self, 
                audio_path: str, 
                output_dir: str = None, 
                include_bass: bool = True) -> Dict[str, str]:
        """
        Complete stem separation pipeline.
        
        Args:
            audio_path: Path to audio file
            output_dir: Directory to save stems (if None, don't export files)
            include_bass: Whether to separate bass from harmonic content
            
        Returns:
            Dictionary of stem names to file paths (if output_dir is provided)
            or stem names to audio data (if output_dir is None)
        """
        logger.info(f"Processing {audio_path} for stem separation")
        
        # Separate stems
        stems = self.separate_stems(audio_path, include_bass)
        
        # Export if output directory is provided
        if output_dir:
            base_filename = os.path.splitext(os.path.basename(audio_path))[0]
            return self.export_stems(stems, output_dir, base_filename)
        
        return stems