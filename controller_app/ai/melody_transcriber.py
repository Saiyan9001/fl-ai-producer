"""
Melody transcription module using CREPE for F0 estimation and librosa for onset detection
"""
import os
import logging
import numpy as np
import librosa
import crepe
import pretty_midi
from scipy.signal import medfilt
from typing import List, Dict, Tuple, Optional, Union

logger = logging.getLogger(__name__)

class MelodyTranscriber:
    """
    A class for transcribing melodies from audio files using CREPE for pitch detection
    and librosa for onset detection.
    """
    
    def __init__(self, 
                 sample_rate: int = 22050, 
                 hop_length: int = 512,
                 crepe_step_size: int = 10,
                 crepe_model: str = 'full',
                 confidence_threshold: float = 0.8,
                 onset_threshold: float = 0.5,
                 median_filter_width: int = 3):
        """
        Initialize the transcriber with given parameters.
        
        Args:
            sample_rate: Audio sample rate to use
            hop_length: Hop length for feature extraction
            crepe_step_size: Step size in milliseconds for CREPE
            crepe_model: CREPE model size ('tiny', 'small', 'medium', 'large', or 'full')
            confidence_threshold: Minimum confidence threshold for pitch detection
            onset_threshold: Threshold for onset detection
            median_filter_width: Width of the median filter for smoothing pitch
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.crepe_step_size = crepe_step_size
        self.crepe_model = crepe_model
        self.confidence_threshold = confidence_threshold
        self.onset_threshold = onset_threshold
        self.median_filter_width = median_filter_width
        
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and resample if necessary.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        logger.info(f"Loading audio from {audio_path}")
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        return y, sr
        
    def detect_pitch(self, audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect pitch using CREPE.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Tuple of (time, frequency, confidence)
        """
        logger.info("Detecting pitch with CREPE")
        time, frequency, confidence, _ = crepe.predict(
            audio, 
            self.sample_rate,
            step_size=self.crepe_step_size,
            model_capacity=self.crepe_model,
            viterbi=True
        )
        
        # Apply confidence thresholding
        frequency[confidence < self.confidence_threshold] = 0
        
        # Apply median filtering to smooth out pitch
        if self.median_filter_width > 0:
            frequency = medfilt(frequency, self.median_filter_width)
            
        return time, frequency, confidence
        
    def detect_onsets(self, audio: np.ndarray) -> np.ndarray:
        """
        Detect note onsets in audio.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Array of onset times in seconds
        """
        logger.info("Detecting onsets")
        
        # Get onset strength
        onset_env = librosa.onset.onset_strength(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )
        
        # Detect onsets from the onset strength envelope
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=self.sample_rate,
            hop_length=self.hop_length,
            backtrack=True,
            threshold=self.onset_threshold
        )
        
        # Convert frames to time
        onset_times = librosa.frames_to_time(
            onset_frames, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )
        
        return onset_times
    
    def extract_chroma(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract chroma features for harmony analysis.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Chroma features
        """
        logger.info("Extracting chroma features")
        chroma = librosa.feature.chroma_cqt(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )
        return chroma
        
    def frequency_to_midi_note(self, freq: float) -> int:
        """
        Convert frequency in Hz to MIDI note number.
        
        Args:
            freq: Frequency in Hz
            
        Returns:
            MIDI note number
        """
        if freq <= 0:
            return 0
        return int(round(69 + 12 * np.log2(freq / 440.0)))
    
    def segment_notes(self, 
                      time: np.ndarray, 
                      frequency: np.ndarray, 
                      confidence: np.ndarray,
                      onset_times: np.ndarray) -> List[Dict]:
        """
        Segment the continuous pitch track into discrete notes.
        
        Args:
            time: Time points
            frequency: Frequency values at each time point
            confidence: Confidence values at each time point
            onset_times: Detected onset times
            
        Returns:
            List of note dictionaries with start, end, pitch, and velocity
        """
        logger.info("Segmenting notes")
        notes = []
        
        # If no onsets found, return empty list
        if len(onset_times) == 0:
            return notes
            
        # Add a final "onset" at the end of the audio to close the last note
        onset_times = np.append(onset_times, time[-1])
        
        # Process each segment between onsets
        for i in range(len(onset_times) - 1):
            start_time = onset_times[i]
            end_time = onset_times[i+1]
            
            # Find indices within this segment
            segment_indices = np.where((time >= start_time) & (time < end_time))[0]
            
            if len(segment_indices) == 0:
                continue
                
            # Get frequencies and confidences in this segment
            segment_freqs = frequency[segment_indices]
            segment_confs = confidence[segment_indices]
            
            # Filter out zeros and low confidence values
            valid_indices = segment_freqs > 0
            if not np.any(valid_indices):
                continue
                
            valid_freqs = segment_freqs[valid_indices]
            valid_confs = segment_confs[valid_indices]
            
            if len(valid_freqs) == 0:
                continue
                
            # Use the most common frequency with highest confidence
            # (simple approach - could be improved with clustering)
            median_freq = np.median(valid_freqs)
            mean_conf = np.mean(valid_confs)
            
            # Convert frequency to MIDI note
            midi_note = self.frequency_to_midi_note(median_freq)
            
            # Skip if out of MIDI range (0-127)
            if not (0 <= midi_note <= 127):
                continue
                
            # Scale confidence to velocity (0-127)
            velocity = int(min(127, max(40, mean_conf * 127)))
            
            # Create note dictionary
            note = {
                "start": float(start_time),
                "end": float(end_time),
                "pitch": int(midi_note),
                "velocity": int(velocity)
            }
            notes.append(note)
            
        return notes
    
    def quantize_notes(self, notes: List[Dict], 
                       bpm: float = 120.0, 
                       ppq: int = 960,
                       quantize_start: bool = True,
                       quantize_duration: bool = True) -> List[Dict]:
        """
        Quantize notes to a musical grid based on BPM.
        
        Args:
            notes: List of note dictionaries
            bpm: Tempo in beats per minute
            ppq: Pulses per quarter note (PPQN)
            quantize_start: Whether to quantize note start times
            quantize_duration: Whether to quantize note durations
            
        Returns:
            Quantized notes
        """
        logger.info(f"Quantizing notes to {bpm} BPM grid")
        
        # Calculate time per quarter note
        seconds_per_quarter = 60.0 / bpm
        # Calculate seconds per tick
        seconds_per_tick = seconds_per_quarter / ppq
        
        quantized_notes = []
        for note in notes:
            start_time = note["start"]
            end_time = note["end"]
            
            # Convert to ticks
            start_tick = start_time / seconds_per_tick
            end_tick = end_time / seconds_per_tick
            
            if quantize_start:
                # Quantize to nearest 16th note (ppq/4)
                grid_size = ppq / 4
                start_tick = round(start_tick / grid_size) * grid_size
                
            if quantize_duration:
                # Quantize to nearest 16th note
                grid_size = ppq / 4
                duration_ticks = end_tick - start_tick
                duration_ticks = max(grid_size, round(duration_ticks / grid_size) * grid_size)
                end_tick = start_tick + duration_ticks
            
            # Convert back to seconds
            quantized_start = float(start_tick * seconds_per_tick)
            quantized_end = float(end_tick * seconds_per_tick)
            
            # Create quantized note
            quantized_note = {
                "start": quantized_start,
                "end": quantized_end,
                "pitch": note["pitch"],
                "velocity": note["velocity"]
            }
            quantized_notes.append(quantized_note)
            
        return quantized_notes
    
    def estimate_chords(self, 
                        audio: np.ndarray, 
                        notes: List[Dict],
                        bpm: float = 120.0) -> List[Dict]:
        """
        Estimate chords based on chroma features.
        
        Args:
            audio: Audio data
            notes: Melody notes
            bpm: Tempo in BPM
            
        Returns:
            List of chord dictionaries
        """
        logger.info("Estimating chords")
        
        # Extract chroma features
        chroma = self.extract_chroma(audio)
        
        # Simple chord templates (major and minor triads)
        chord_templates = {
            'C': np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]),  # C major
            'Cm': np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]), # C minor
            # Add more chord templates as needed
        }
        
        # Segment audio into measures based on BPM
        seconds_per_measure = 60.0 / bpm * 4  # Assuming 4/4 time
        total_duration = len(audio) / self.sample_rate
        num_measures = int(np.ceil(total_duration / seconds_per_measure))
        
        chord_notes = []
        for measure in range(num_measures):
            start_time = measure * seconds_per_measure
            end_time = min((measure + 1) * seconds_per_measure, total_duration)
            
            # Get chroma for this measure
            start_frame = librosa.time_to_frames(start_time, sr=self.sample_rate, hop_length=self.hop_length)
            end_frame = librosa.time_to_frames(end_time, sr=self.sample_rate, hop_length=self.hop_length)
            measure_chroma = np.mean(chroma[:, start_frame:end_frame], axis=1)
            
            # Normalize
            if np.sum(measure_chroma) > 0:
                measure_chroma = measure_chroma / np.sum(measure_chroma)
            
            # Find best matching chord
            best_chord = "N"  # No chord
            best_score = -1
            
            for root in range(12):  # For all possible roots
                for name, template in chord_templates.items():
                    # Rotate template to current root
                    shifted_template = np.roll(template, root)
                    
                    # Calculate match score (dot product)
                    score = np.dot(measure_chroma, shifted_template)
                    
                    if score > best_score:
                        best_score = score
                        chord_root = (root + 9) % 12  # Map back to C=0
                        root_name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][chord_root]
                        chord_type = name.replace('C', '')
                        best_chord = root_name + chord_type
            
            # Create chord notes based on the detected chord
            root_note = {'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64, 
                        'F': 65, 'F#': 66, 'G': 67, 'G#': 68, 'A': 69, 
                        'A#': 70, 'B': 71}[best_chord[0:1] if len(best_chord) == 1 else best_chord[0:2]]
                
            # Major chord
            if best_chord.endswith('m'):  # Minor chord
                chord_notes.extend([
                    {"start": start_time, "end": end_time, "pitch": root_note, "velocity": 70},
                    {"start": start_time, "end": end_time, "pitch": root_note + 3, "velocity": 70},  # Minor third
                    {"start": start_time, "end": end_time, "pitch": root_note + 7, "velocity": 70}   # Perfect fifth
                ])
            else:  # Major chord
                chord_notes.extend([
                    {"start": start_time, "end": end_time, "pitch": root_note, "velocity": 70},
                    {"start": start_time, "end": end_time, "pitch": root_note + 4, "velocity": 70},  # Major third
                    {"start": start_time, "end": end_time, "pitch": root_note + 7, "velocity": 70}   # Perfect fifth
                ])
        
        return chord_notes
    
    def detect_bass(self, audio: np.ndarray, bpm: float = 120.0) -> List[Dict]:
        """
        Extract bass line using low-frequency filtering.
        
        Args:
            audio: Audio data
            bpm: Tempo in BPM
            
        Returns:
            List of bass note dictionaries
        """
        logger.info("Extracting bass line")
        
        # Apply low-pass filter to isolate bass frequencies
        bass_audio = librosa.effects.preemphasis(audio, coef=0.95, return_zeropad=True)
        
        # Filter to keep only low frequencies (below 250 Hz)
        bass_audio = librosa.effects.low_pass_filter(bass_audio, sr=self.sample_rate, cutoff=250)
        
        # Detect pitch on bass audio
        time, frequency, confidence = self.detect_pitch(bass_audio)
        
        # Detect onsets with emphasis on low frequencies
        onset_env = librosa.onset.onset_strength(
            y=bass_audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length,
            feature=librosa.feature.melspectrogram,
            fmax=250  # Focus on low frequencies
        )
        
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=self.sample_rate,
            hop_length=self.hop_length,
            backtrack=True,
            threshold=self.onset_threshold * 0.8  # Slightly lower threshold for bass
        )
        
        onset_times = librosa.frames_to_time(
            onset_frames, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )
        
        # Segment notes
        bass_notes = self.segment_notes(time, frequency, confidence, onset_times)
        
        # Filter notes to keep only those in bass range (MIDI notes 24-59)
        bass_notes = [note for note in bass_notes if 24 <= note["pitch"] <= 59]
        
        # Quantize notes
        bass_notes = self.quantize_notes(bass_notes, bpm=bpm)
        
        return bass_notes
    
    def detect_percussion(self, audio: np.ndarray) -> List[Dict]:
        """
        Detect percussion/drum hits using onset detection with spectral features.
        
        Args:
            audio: Audio data
            
        Returns:
            List of percussion hit dictionaries
        """
        logger.info("Detecting percussion hits")
        
        # Compute spectral flux onset strength
        onset_env = librosa.onset.onset_strength(
            y=audio, 
            sr=self.sample_rate,
            hop_length=self.hop_length,
            feature=librosa.feature.spectral_flux
        )
        
        # Detect onsets
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=self.sample_rate,
            hop_length=self.hop_length,
            backtrack=False,
            threshold=self.onset_threshold
        )
        
        onset_times = librosa.frames_to_time(
            onset_frames, 
            sr=self.sample_rate,
            hop_length=self.hop_length
        )
        
        # Simple drum mapping based on spectral characteristics
        percussion_notes = []
        
        for i, onset_time in enumerate(onset_times):
            # Calculate frame index for this onset
            frame_idx = onset_frames[i]
            
            # Extract spectral features at the onset
            if frame_idx < len(onset_env):
                # Get a small window after the onset
                window_start = int(onset_time * self.sample_rate)
                window_end = min(len(audio), window_start + int(0.05 * self.sample_rate))  # 50ms window
                
                if window_start < len(audio):
                    window = audio[window_start:window_end]
                    
                    if len(window) > 0:
                        # Extract spectral features
                        spec_centroid = librosa.feature.spectral_centroid(
                            y=window, sr=self.sample_rate).mean()
                        spec_flatness = librosa.feature.spectral_flatness(
                            y=window, S=None).mean()
                        
                        # Simple drum classification based on spectral features
                        if spec_centroid < 1000:  # Low frequency content (kick drum)
                            midi_note = 36  # C1 (General MIDI kick drum)
                            velocity = 100
                        elif spec_centroid > 3000:  # High frequency content (hi-hat/cymbals)
                            midi_note = 42  # F#1 (General MIDI closed hi-hat)
                            velocity = 90
                        else:  # Mid frequency content (snare)
                            midi_note = 38  # D1 (General MIDI snare drum)
                            velocity = 95
                        
                        # Add percussion note
                        percussion_notes.append({
                            "start": float(onset_time),
                            "end": float(onset_time + 0.1),  # Fixed duration for percussion
                            "pitch": int(midi_note),
                            "velocity": int(velocity)
                        })
        
        return percussion_notes
    
    def create_midi_file(self, 
                        melody_notes: List[Dict], 
                        bass_notes: List[Dict] = None,
                        chord_notes: List[Dict] = None,
                        percussion_notes: List[Dict] = None,
                        bpm: float = 120.0) -> pretty_midi.PrettyMIDI:
        """
        Create a multi-track MIDI file from note data.
        
        Args:
            melody_notes: List of melody note dictionaries
            bass_notes: List of bass note dictionaries
            chord_notes: List of chord note dictionaries
            percussion_notes: List of percussion note dictionaries
            bpm: Tempo in BPM
            
        Returns:
            PrettyMIDI object
        """
        logger.info("Creating MIDI file")
        
        # Create PrettyMIDI object
        midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
        
        # Create melody instrument
        melody_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
        melody_instrument = pretty_midi.Instrument(program=melody_program)
        melody_instrument.name = "Melody"
        
        # Add melody notes
        for note in melody_notes:
            n = pretty_midi.Note(
                velocity=note["velocity"],
                pitch=note["pitch"],
                start=note["start"],
                end=note["end"]
            )
            melody_instrument.notes.append(n)
        
        midi.instruments.append(melody_instrument)
        
        # Add bass if available
        if bass_notes:
            bass_program = pretty_midi.instrument_name_to_program('Electric Bass (finger)')
            bass_instrument = pretty_midi.Instrument(program=bass_program)
            bass_instrument.name = "Bass"
            
            for note in bass_notes:
                n = pretty_midi.Note(
                    velocity=note["velocity"],
                    pitch=note["pitch"],
                    start=note["start"],
                    end=note["end"]
                )
                bass_instrument.notes.append(n)
                
            midi.instruments.append(bass_instrument)
        
        # Add chords if available
        if chord_notes:
            chord_program = pretty_midi.instrument_name_to_program('String Ensemble 1')
            chord_instrument = pretty_midi.Instrument(program=chord_program)
            chord_instrument.name = "Chords"
            
            for note in chord_notes:
                n = pretty_midi.Note(
                    velocity=note["velocity"],
                    pitch=note["pitch"],
                    start=note["start"],
                    end=note["end"]
                )
                chord_instrument.notes.append(n)
                
            midi.instruments.append(chord_instrument)
        
        # Add percussion if available
        if percussion_notes:
            percussion_instrument = pretty_midi.Instrument(program=0, is_drum=True)
            percussion_instrument.name = "Percussion"
            
            for note in percussion_notes:
                n = pretty_midi.Note(
                    velocity=note["velocity"],
                    pitch=note["pitch"],
                    start=note["start"],
                    end=note["end"]
                )
                percussion_instrument.notes.append(n)
                
            midi.instruments.append(percussion_instrument)
        
        return midi
    
    def transcribe(self, 
                  audio_path: str, 
                  bpm: float = 120.0,
                  quantize: bool = True,
                  extract_bass: bool = True,
                  extract_chords: bool = True,
                  extract_percussion: bool = True) -> Dict:
        """
        Complete transcription pipeline from audio to MIDI data.
        
        Args:
            audio_path: Path to audio file
            bpm: Tempo in BPM
            quantize: Whether to quantize notes
            extract_bass: Whether to extract bass line
            extract_chords: Whether to extract chords
            extract_percussion: Whether to extract percussion
            
        Returns:
            Dictionary with transcription results and MIDI data
        """
        logger.info(f"Starting transcription of {audio_path} at {bpm} BPM")
        
        # Load audio
        audio, sr = self.load_audio(audio_path)
        
        # Detect melody
        time, frequency, confidence = self.detect_pitch(audio)
        onset_times = self.detect_onsets(audio)
        melody_notes = self.segment_notes(time, frequency, confidence, onset_times)
        
        # Quantize if requested
        if quantize:
            melody_notes = self.quantize_notes(melody_notes, bpm=bpm)
        
        # Extract additional elements if requested
        bass_notes = self.detect_bass(audio, bpm) if extract_bass else []
        chord_notes = self.estimate_chords(audio, melody_notes, bpm) if extract_chords else []
        percussion_notes = self.detect_percussion(audio) if extract_percussion else []
        
        # Create MIDI
        midi_data = self.create_midi_file(
            melody_notes, 
            bass_notes, 
            chord_notes, 
            percussion_notes, 
            bpm
        )
        
        return {
            "melody_notes": melody_notes,
            "bass_notes": bass_notes,
            "chord_notes": chord_notes,
            "percussion_notes": percussion_notes,
            "midi_data": midi_data
        }

    def export_midi(self, midi_data: pretty_midi.PrettyMIDI, output_path: str) -> str:
        """
        Export MIDI data to a file.
        
        Args:
            midi_data: PrettyMIDI object
            output_path: Path to save the MIDI file
            
        Returns:
            Path to saved MIDI file
        """
        logger.info(f"Exporting MIDI to {output_path}")
        midi_data.write(output_path)
        return output_path