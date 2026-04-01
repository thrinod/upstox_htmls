import PyPDF2
import pyttsx3
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import time
import gc

class SimplePDFReader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Simple PDF Reader with Natural Speech")
        self.root.geometry("900x650")
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.setup_natural_voice()
        
        # Book storage
        self.book_chunks = []
        self.current_chunk_index = 0
        self.chunk_size = 3000
        self.total_chunks = 0
        self.book_title = ""
        
        # Reading state
        self.is_speaking = False
        self.current_sentence_index = 0
        
        self.create_ui()
    
    def setup_natural_voice(self):
        """Setup the most natural voice available"""
        voices = self.tts_engine.getProperty('voices')
        
        # Find the best available voice (prefer female voices as they're usually more natural)
        best_voice = None
        voice_priorities = ['zira', 'hazel', 'female', 'woman', 'susan', 'anna', 'jenny']
        
        for priority in voice_priorities:
            for voice in voices:
                if priority in voice.name.lower():
                    best_voice = voice
                    break
            if best_voice:
                break
        
        # If no preferred voice found, use the second voice (usually better than default)
        if not best_voice and len(voices) > 1:
            best_voice = voices[1]
        elif not best_voice and voices:
            best_voice = voices[0]
        
        if best_voice:
            self.tts_engine.setProperty('voice', best_voice.id)
        
        # Optimize settings for natural speech
        self.tts_engine.setProperty('rate', 170)    # Slightly slower for better comprehension
        self.tts_engine.setProperty('volume', 0.9)  # Clear volume
    
    def create_ui(self):
        """Create simple, clean interface"""
        # Main container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header
        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Button(header_frame, text="📖 Load PDF Book", 
                 command=self.select_pdf, bg='#4CAF50', fg='white',
                 font=('Arial', 13, 'bold'), pady=8).pack(side=tk.LEFT)
        
        self.file_info = tk.Label(header_frame, text="No book loaded", 
                                 font=('Arial', 11), fg='#555')
        self.file_info.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress section
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(progress_frame, text="Progress:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          length=300, height=20)
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 10))
        
        self.progress_label = tk.Label(progress_frame, text="0 / 0", font=('Arial', 10))
        self.progress_label.pack(side=tk.LEFT)
        
        # Navigation
        tk.Button(progress_frame, text="◀", command=self.previous_chapter, 
                 font=('Arial', 12)).pack(side=tk.RIGHT, padx=2)
        tk.Button(progress_frame, text="▶", command=self.next_chapter, 
                 font=('Arial', 12)).pack(side=tk.RIGHT, padx=2)
        
        # Current section info
        self.section_label = tk.Label(main_frame, text="", font=('Arial', 10, 'bold'), 
                                     fg='#2196F3')
        self.section_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Text display
        self.text_display = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, font=('Georgia', 12),
            height=20, bg='#fefefe', fg='#333',
            relief=tk.FLAT, bd=8, padx=20, pady=20
        )
        self.text_display.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Controls
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        # Main controls
        buttons_frame = tk.Frame(control_frame)
        buttons_frame.pack(side=tk.LEFT)
        
        self.play_button = tk.Button(buttons_frame, text="▶️ Start Reading", 
                                   command=self.toggle_reading, bg='#2196F3', fg='white',
                                   font=('Arial', 12, 'bold'), width=15, pady=8)
        self.play_button.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(buttons_frame, text="⏹️ Stop", 
                 command=self.stop_reading, bg='#f44336', fg='white',
                 font=('Arial', 12, 'bold'), width=10, pady=8).pack(side=tk.LEFT, padx=5)
        
        # Settings
        settings_frame = tk.Frame(control_frame)
        settings_frame.pack(side=tk.RIGHT)
        
        tk.Label(settings_frame, text="Speed:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.speed_var = tk.IntVar(value=170)
        tk.Scale(settings_frame, from_=120, to=220, orient=tk.HORIZONTAL, 
                variable=self.speed_var, command=self.update_speed, 
                length=100).pack(side=tk.LEFT, padx=5)
        
        self.auto_advance = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Auto continue", 
                      variable=self.auto_advance).pack(side=tk.LEFT, padx=(15, 0))
        
        # Status
        self.status = tk.Label(self.root, text="Ready to load your book", 
                              relief=tk.SUNKEN, anchor=tk.W, bg='#f8f8f8')
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def select_pdf(self):
        """Load PDF book"""
        file_path = filedialog.askopenfilename(
            title="Select PDF Book",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if file_path:
            self.status.config(text="Loading book...")
            self.root.update()
            
            # Load in background
            threading.Thread(target=self.load_pdf, args=(file_path,), daemon=True).start()
    
    def load_pdf(self, pdf_path):
        """Load and process PDF"""
        try:
            self.book_title = pdf_path.split('/')[-1].replace('.pdf', '')
            
            # Clear previous book
            self.book_chunks.clear()
            gc.collect()
            
            full_text = ""
            
            # Extract text
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += self.clean_page_text(page_text) + "\n\n"
                    
                    # Update progress
                    if page_num % 10 == 0:
                        progress = f"Reading page {page_num + 1}/{total_pages}..."
                        self.root.after(0, lambda p=progress: self.status.config(text=p))
            
            # Improve text for speech
            self.root.after(0, lambda: self.status.config(text="Preparing text for reading..."))
            improved_text = self.make_speech_friendly(full_text)
            
            # Split into chapters
            self.create_chapters(improved_text)
            
            # Update UI
            self.root.after(0, self.update_after_loading)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Could not load PDF: {str(e)}"))
    
    def clean_page_text(self, text):
        """Clean text from PDF and remove spacing issues"""
        # Remove all excessive whitespace first
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Fix broken words (common in PDFs)
        text = re.sub(r'([a-z])\s+([a-z])\s+([a-z])', r'\1\2\3', text)  # Remove spaces in broken words
        
        # Fix sentences that got broken
        text = re.sub(r'([a-z])\s*\n\s*([a-z])', r'\1\2', text)
        
        # Fix capitalization issues from PDF extraction
        text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)
        
        return text
    
    def make_speech_friendly(self, text):
        """Make text better for speech by removing extra spaces and fixing issues"""
        # Step 1: Aggressive space trimming
        text = re.sub(r'\s+', ' ', text.strip())  # Replace all whitespace with single space
        
        # Step 2: Fix common PDF extraction issues
        text = re.sub(r'\.{2,}', '.', text)  # Multiple dots to single
        text = re.sub(r'\s*\.\s*', '. ', text)  # Proper spacing around periods
        text = re.sub(r'\s*,\s*', ', ', text)  # Proper spacing around commas
        text = re.sub(r'\s*;\s*', '; ', text)  # Proper spacing around semicolons
        text = re.sub(r'\s*:\s*', ': ', text)  # Proper spacing around colons
        
        # Step 3: Fix sentence boundaries
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Step 4: Remove extra spaces around quotes and parentheses
        text = re.sub(r'\s*"\s*', ' "', text)  # Before opening quotes
        text = re.sub(r'\s*"\s*', '" ', text)  # After closing quotes
        text = re.sub(r'\s*\(\s*', ' (', text)  # Before opening parentheses
        text = re.sub(r'\s*\)\s*', ') ', text)  # After closing parentheses
        
        # Step 5: Expand abbreviations for clearer speech
        replacements = {
            r'\bDr\.\s*': 'Doctor ',
            r'\bMr\.\s*': 'Mister ',
            r'\bMrs\.\s*': 'Missus ',
            r'\bMs\.\s*': 'Miss ',
            r'\bProf\.\s*': 'Professor ',
            r'\betc\.\s*': 'etcetera ',
            r'\bi\.\s*e\.\s*': 'that is ',
            r'\be\.\s*g\.\s*': 'for example ',
            r'\bvs\.\s*': 'versus ',
            r'\bUSA\b': 'United States of America',
            r'\bUK\b': 'United Kingdom',
            # Fix numbers that got separated
            r'(\d)\s+(\d)': r'\1\2',  # Fix separated numbers like "1 0 0" -> "100"
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Step 6: Final cleanup - remove multiple spaces that might have been created
        text = re.sub(r'\s{2,}', ' ', text)
        
        # Step 7: Add natural pauses for better speech flow
        text = re.sub(r'([.!?])\s*', r'\1  ', text)  # Double space after sentences
        text = re.sub(r'([,;:])\s*', r'\1 ', text)   # Single space after other punctuation
        
        # Step 8: Remove any remaining problematic spacing
        text = text.strip()
        
        return text
    
    def create_chapters(self, text):
        """Split text into readable chapters"""
        # Split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chapter = ""
        chapter_num = 1
        
        for paragraph in paragraphs:
            if len(current_chapter) + len(paragraph) > self.chunk_size and current_chapter:
                self.book_chunks.append({
                    'text': current_chapter.strip(),
                    'number': chapter_num,
                    'title': f"Chapter {chapter_num}"
                })
                current_chapter = paragraph + "\n\n"
                chapter_num += 1
            else:
                current_chapter += paragraph + "\n\n"
        
        # Add final chapter
        if current_chapter.strip():
            self.book_chunks.append({
                'text': current_chapter.strip(),
                'number': chapter_num,
                'title': f"Chapter {chapter_num}"
            })
        
        self.total_chunks = len(self.book_chunks)
        self.current_chunk_index = 0
    
    def update_after_loading(self):
        """Update UI after loading"""
        if self.book_chunks:
            self.show_current_chapter()
            self.update_progress()
            self.file_info.config(text=f"📖 {self.book_title} ({self.total_chunks} chapters)")
            self.status.config(text=f"✅ Loaded {self.book_title} - {self.total_chunks} chapters")
    
    def show_current_chapter(self):
        """Display current chapter"""
        if self.book_chunks:
            chapter = self.book_chunks[self.current_chunk_index]
            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(1.0, chapter['text'])
            self.section_label.config(text=f"📄 {chapter['title']}")
    
    def update_progress(self):
        """Update progress display"""
        if self.book_chunks:
            progress = (self.current_chunk_index + 1) / self.total_chunks * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{self.current_chunk_index + 1} / {self.total_chunks}")
    
    def toggle_reading(self):
        """Start or pause reading"""
        if not self.book_chunks:
            messagebox.showwarning("No Book", "Please load a PDF book first.")
            return
        
        if self.is_speaking:
            self.pause_reading()
        else:
            self.start_reading()
    
    def start_reading(self):
        """Start reading current chapter"""
        self.is_speaking = True
        self.play_button.config(text="⏸️ Pause", bg='#FF9800')
        
        # Start reading in background
        threading.Thread(target=self.read_chapters, daemon=True).start()
    
    def pause_reading(self):
        """Pause reading"""
        self.is_speaking = False
        self.tts_engine.stop()
        self.play_button.config(text="▶️ Continue", bg='#2196F3')
    
    def stop_reading(self):
        """Stop reading"""
        self.is_speaking = False
        self.tts_engine.stop()
        self.play_button.config(text="▶️ Start Reading", bg='#2196F3')
        self.current_sentence_index = 0
    
    def read_chapters(self):
        """Read through chapters continuously"""
        try:
            while self.is_speaking and self.current_chunk_index < len(self.book_chunks):
                chapter = self.book_chunks[self.current_chunk_index]
                
                # Update status
                self.root.after(0, lambda: self.status.config(
                    text=f"🎵 Reading {chapter['title']}..."
                ))
                
                # Split into sentences for better control
                sentences = re.split(r'[.!?]+', chapter['text'])
                
                for i, sentence in enumerate(sentences):
                    if not self.is_speaking:
                        return
                    
                    sentence = sentence.strip()
                    if len(sentence) > 10:
                        self.tts_engine.say(sentence + ".")
                        self.tts_engine.runAndWait()
                
                # Auto advance to next chapter
                if self.auto_advance.get() and self.is_speaking:
                    self.current_chunk_index += 1
                    if self.current_chunk_index < len(self.book_chunks):
                        self.root.after(0, self.show_current_chapter)
                        self.root.after(0, self.update_progress)
                        time.sleep(1)  # Brief pause between chapters
                else:
                    break
            
            # Finished reading
            if self.current_chunk_index >= len(self.book_chunks):
                self.root.after(0, lambda: self.status.config(text="🎉 Finished reading the book!"))
            
        except Exception as e:
            print(f"Reading error: {e}")
        finally:
            self.is_speaking = False
            self.root.after(0, lambda: self.play_button.config(text="▶️ Start Reading", bg='#2196F3'))
    
    def previous_chapter(self):
        """Go to previous chapter"""
        if self.current_chunk_index > 0:
            self.current_chunk_index -= 1
            self.show_current_chapter()
            self.update_progress()
    
    def next_chapter(self):
        """Go to next chapter"""
        if self.current_chunk_index < len(self.book_chunks) - 1:
            self.current_chunk_index += 1
            self.show_current_chapter()
            self.update_progress()
    
    def update_speed(self, value):
        """Update reading speed"""
        self.tts_engine.setProperty('rate', int(value))
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

# Run the app
if __name__ == "__main__":
    app = SimplePDFReader()
    app.run()