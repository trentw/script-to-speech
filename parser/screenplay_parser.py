from enum import Enum, auto
from typing import List, Dict, Optional
import re
from dataclasses import dataclass

class State(Enum):
    TITLE = auto()
    SCENE_HEADING = auto()
    ACTION = auto()
    SPEAKER_ATTRIBUTION = auto()
    DIALOG = auto()
    DIALOG_MODIFIER = auto()
    DUAL_SPEAKER_ATTRIBUTION = auto()
    DUAL_DIALOG = auto()


@dataclass
class Chunk:
    type: str
    speaker: str
    text: List[str]

class IndentationContext:
    def __init__(self):
        self.last_speaker_indent = None
        self.last_dialog_indent = None
        self.last_action_indent = None
        self.current_indent = None
        
    def update(self, state: State, indent: int):
        self.current_indent = indent
        if state == State.SPEAKER_ATTRIBUTION:
            self.last_speaker_indent = indent
        elif state == State.DIALOG:
            self.last_dialog_indent = indent
        elif state == State.ACTION:
            self.last_action_indent = indent

class ScreenplayParser:
    def __init__(self):
        self.state = State.TITLE  # Start in TITLE state
        self.has_left_title = False 
        self.current_speaker = None
        self.current_chunk = None
        self.chunks = []
        self.indent_context = IndentationContext()
        
    def calculate_probabilities(self, line: str, indentation: int) -> Dict[State, float]:
        """Calculate probability scores for each possible state."""
        probs = {
            State.TITLE: 0.0 if self.has_left_title else 2.0,
            State.ACTION: 0.1,
            State.DIALOG: 0.1,
            State.SPEAKER_ATTRIBUTION: 0.1,
            State.DIALOG_MODIFIER: 0.1,
            State.SCENE_HEADING: 0.1,
            State.DUAL_SPEAKER_ATTRIBUTION: 0.1,
            State.DUAL_DIALOG: 0.1
        }
        
        stripped = line.strip()

        # For dual speaker detection - more lenient spacing requirement
        if (stripped.isupper() and indentation < 30 and  
            re.search(r'[A-Z]+\s{8,}[A-Z]+', stripped)):  # Only need 8+ spaces between speakers
            probs[State.DUAL_SPEAKER_ATTRIBUTION] += 1.0

        # For dual dialog
        if self.state == State.DUAL_SPEAKER_ATTRIBUTION or self.state == State.DUAL_DIALOG:
            if not stripped:  
                # Just reset dual dialog probability on blank line, don't force action
                probs[State.DUAL_DIALOG] = 0.1  # Back to baseline
            elif indentation < 20:  # Less indented dialog
                probs[State.DUAL_DIALOG] += 0.8
                probs[State.ACTION] -= 0.8

        # Scene heading indicators
        if re.match(r'^(\s*\d+\s+)?(INT\.|EXT\.)', stripped):
            probs[State.SCENE_HEADING] += 0.8
            probs[State.TITLE] = 0.0 # exit case for title state
            return probs
        
        # Relative indentation effects
        if self.indent_context.last_dialog_indent is not None:
            indent_change = indentation - self.indent_context.last_dialog_indent
            if abs(indent_change) <= 2:
                probs[State.DIALOG] += 0.4
            elif indent_change < -5:
                probs[State.ACTION] += 0.6
                probs[State.DIALOG] -= 0.1
        
        # Dialog modifier detection
        if self.state == State.DIALOG_MODIFIER:
            # If we're in a dialog modifier, keep high probability
            probs[State.DIALOG_MODIFIER] += 0.7
        elif stripped.startswith('('):
            # Starting a new dialog modifier
            if self.state in [State.DIALOG, State.SPEAKER_ATTRIBUTION]:
                # Extra bonus if it's a complete parenthetical on one line
                if stripped.endswith(')'):
                    probs[State.DIALOG_MODIFIER] += 0.9
                else:
                    probs[State.DIALOG_MODIFIER] += 0.7
        
        # Speaker attribution
        if (indentation >= 30 and stripped.isupper() and 
            not any(word in stripped.lower() for word in ['int.', 'ext.'])):
            probs[State.SPEAKER_ATTRIBUTION] += 0.6
            if self.state == State.ACTION:
                probs[State.SPEAKER_ATTRIBUTION] += 0.2
        
        # Dialog indicators with stronger context
        if self.current_speaker:
            if 20 <= indentation < 30:
                probs[State.DIALOG] += 0.4
                if self.state == State.SPEAKER_ATTRIBUTION:
                    probs[State.DIALOG] += 0.3
                elif self.state == State.DIALOG_MODIFIER:
                    probs[State.DIALOG] += 0.3
        
        # Action state
        if indentation < 20:
            probs[State.ACTION] += 0.4
            if self.state == State.DIALOG and self.indent_context.last_dialog_indent is not None:
                if indentation < self.indent_context.last_dialog_indent:
                    probs[State.ACTION] += 0.3
                    probs[State.DIALOG] -= 0.2
            probs[State.TITLE] = 0.0 # exit case for title state
        
        return probs
    
    def determine_state(self, line: str, indentation: int) -> Optional[State]:
        """Determine state based on probability calculations."""
        if not line.strip():
            return None
            
        probs = self.calculate_probabilities(line, indentation)
        
        # Log probabilities for analysis
        print(f"\nProbability Analysis for line: {line.strip()[:40]}...")
        print(f"Current state: {self.state}")
        print(f"Indentation: {indentation}")
        for state, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
            print(f"{state.name}: {prob:.2f}")
        
        # Return the state with highest probability
        return max(probs.items(), key=lambda x: x[1])[0]
    
    def is_page_number(self, line: str) -> bool:
        """Check if line is a page number."""
        stripped = line.strip()
        return bool(re.match(r'^\s*\d+\.?\s*$', stripped))
    
    def get_indentation(self, line: str) -> int:
        """Get line indentation level."""
        return len(line) - len(line.lstrip())
    
    def handle_state_transition(self, line: str, new_state: Optional[State]):
        """Handle transition between states."""

        if new_state and new_state != State.TITLE:
            self.has_left_title = True
            
        if new_state is None:
            return
            
        # Update indentation context
        indentation = self.get_indentation(line)
        self.indent_context.update(new_state, indentation)
            
        if new_state != self.state or self.current_chunk is None:
            if self.current_chunk and self.current_chunk.text:
                self.chunks.append(self.current_chunk)
            
            chunk_type = new_state.name.lower()
            speaker = 'none'
            
            if new_state == State.SPEAKER_ATTRIBUTION:
                self.current_speaker = re.sub(r'\([^)]*\)', '', line.strip()).strip()
                
            elif new_state == State.DIALOG:
                speaker = self.current_speaker
                
            self.current_chunk = Chunk(
                type=chunk_type,
                speaker=speaker,
                text=[line.rstrip()]
            )
        else:
            self.current_chunk.text.append(line.rstrip())
        
        self.state = new_state
    
    def parse_screenplay(self, text: str) -> List[Dict]:
        """Parse screenplay using probabilistic state machine approach."""
        self.state = State.ACTION
        self.current_speaker = None
        self.current_chunk = None
        self.chunks = []
        self.indent_context = IndentationContext()
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if self.is_page_number(line):
                if self.current_chunk and self.current_chunk.text:
                    self.chunks.append(self.current_chunk)
                
                self.chunks.append(Chunk(
                    type='page_number',
                    speaker='none',
                    text=[line.strip()]
                ))
                
                self.current_chunk = None
                i += 1
                continue
            
            indentation = self.get_indentation(line)
            new_state = self.determine_state(line, indentation)
            self.handle_state_transition(line, new_state)
            
            i += 1
        
        if self.current_chunk and self.current_chunk.text:
            self.chunks.append(self.current_chunk)
        
        return [{
            'type': chunk.type,
            'speaker': chunk.speaker,
            'text': '\n'.join(chunk.text)
        } for chunk in self.chunks]