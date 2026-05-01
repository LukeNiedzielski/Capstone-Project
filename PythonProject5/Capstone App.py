import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import os
import threading
import re
import webbrowser
from dotenv import load_dotenv
from tkinter import filedialog
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Load API key from .env file
load_dotenv()


class LegislativeAIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Polifine | Legislative AI")
        self.root.geometry("1000x700")
        self.root.configure(bg="#151515")
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#171717")
        self.style.configure("TLabel", background="#171717", foreground="#ECECEC", font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", background="#171717", foreground="white", font=("Segoe UI", 22, "bold"))
        self.style.configure("Subtle.TLabel", background="#171717", foreground="#B7B7B7", font=("Segoe UI", 10))
        self.style.configure("Section.TLabel", background="#171717", foreground="#FFFFFF", font=("Segoe UI", 11, "bold"))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                             background="#3D7DFF", foreground="white", borderwidth=0, padding=(12, 8))
        self.style.map("Primary.TButton", background=[("active", "#2F69DE")])
        self.style.configure("Secondary.TButton", font=("Segoe UI", 10, "bold"),
                             background="#3A3A3A", foreground="#EDEDED", borderwidth=0, padding=(12, 8))
        self.style.map("Secondary.TButton", background=[("active", "#505050")])
        self.chat_history = []
        self.current_question = ""
        self.latest_datasource_status = "Waiting for first request."
        self.recency_var = tk.StringVar(value="Any time")
        self.content_type_var = tk.StringVar(value="Mixed")

        self.create_widgets()

    def create_widgets(self):
        # Branding Header
        header = ttk.Frame(self.root, padding=20)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text="Polifine Legislative Assistant", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="AI-powered guidance for laws, policies, and legislative research.",
                  style="Subtle.TLabel").pack(anchor="w", pady=(3, 0))

        # Sidebar
        sidebar = ttk.Frame(self.root, padding=(16, 10))
        sidebar.grid(row=1, column=0, sticky="ns")
        ttk.Label(sidebar, text="History", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.history_list = tk.Listbox(sidebar, bg="#3E3E3E", fg="white", borderwidth=0,
                                       highlightthickness=0, width=26, font=("Segoe UI", 10),
                                       selectbackground="#3D7DFF", activestyle="none")
        self.history_list.pack(fill="both", expand=True)
        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)

        # Main Content Area
        main_frame = ttk.Frame(self.root, padding=(14, 10, 16, 14))
        main_frame.grid(row=1, column=1, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Instructional Text
        instruction_label = ttk.Label(main_frame,
                                      text="Please ask me any questions regarding laws, policies, or anything related to legislation.",
                                      style="Subtle.TLabel")
        instruction_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Input Box
        self.input_box = tk.Text(main_frame, height=4, bg="#3E3E3E", fg="white",
                                 insertbackground="white", borderwidth=0, font=("Segoe UI", 11),
                                 padx=10, pady=8)
        self.input_box.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # Ask Button
        ask_button = ttk.Button(main_frame, text="Ask", style="Primary.TButton", command=self.handle_question)
        ask_button.grid(row=1, column=1, padx=(10, 8), sticky="ne")

        # PDF Export Button
        export_button = ttk.Button(main_frame, text="Export PDF", style="Secondary.TButton",
                                   command=self.export_to_pdf)
        export_button.grid(row=1, column=2, sticky="ne")

        # Filter Row
        filter_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 8))
        filter_frame.grid(row=2, column=0, columnspan=3, sticky="ew")

        ttk.Label(filter_frame, text="Recency", style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
        recency_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.recency_var,
            values=["Any time", "Last 30 days", "Last 90 days", "Current Congress"],
            state="readonly",
            width=18
        )
        recency_filter.grid(row=1, column=0, sticky="w", padx=(0, 10))

        ttk.Label(filter_frame, text="Content Type", style="Subtle.TLabel").grid(row=0, column=1, sticky="w")
        content_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.content_type_var,
            values=["Mixed", "Bills", "Resolutions", "Laws"],
            state="readonly",
            width=18
        )
        content_filter.grid(row=1, column=1, sticky="w", padx=(0, 10))

        # Output Area
        self.output_area = scrolledtext.ScrolledText(main_frame, bg="#30343C", fg="#F2F2F2",
                                                     borderwidth=0, wrap=tk.WORD, font=("Segoe UI", 11),
                                                     padx=10, pady=10)
        self.output_area.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(0, 8))

        # References Section
        references_label = ttk.Label(main_frame, text="References", style="Section.TLabel")
        references_label.grid(row=4, column=0, sticky="w", pady=(6, 5))

        self.references_box = tk.Text(main_frame, height=6, bg="#242A33", fg="#E6E6E6",
                                      insertbackground="white", borderwidth=0, wrap=tk.WORD,
                                      font=("Segoe UI", 10), cursor="arrow", padx=10, pady=8)
        self.references_box.grid(row=5, column=0, columnspan=3, sticky="ew")
        self.update_references_box([])

        # Datasource Status Section
        datasource_label = ttk.Label(main_frame, text="Datasource Status", style="Section.TLabel")
        datasource_label.grid(row=6, column=0, sticky="w", pady=(8, 5))
        self.datasource_box = tk.Text(main_frame, height=6, bg="#1E232B", fg="#CDE3FF",
                                      insertbackground="white", borderwidth=0, wrap=tk.WORD,
                                      font=("Consolas", 9), padx=10, pady=8)
        self.datasource_box.grid(row=7, column=0, columnspan=3, sticky="ew")
        self.update_datasource_box(self.latest_datasource_status)

        # Bottom Metadata
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(bottom_frame, text="Source Verification: Active", style="Subtle.TLabel").pack(anchor="w")

    def handle_question(self):
        question = self.input_box.get("1.0", tk.END).strip()
        if not question: return

        self.current_question = question
        active_filters = self.get_active_filters()
        history_index = len(self.chat_history)
        self.chat_history.append({"question": question, "response": None, "filters": active_filters})
        self.history_list.insert(tk.END, question)
        self.output_area.delete("1.0", tk.END)
        self.output_area.insert(tk.END, "Analyzing legislative data...")

        threading.Thread(target=self.process_question, args=(question, history_index, active_filters)).start()

    def process_question(self, question, history_index, filters):
        response, datasource_status = self.call_deepseek(question, filters)
        self.root.after(0, self.display_response, response, history_index, datasource_status)

    def display_response(self, response, history_index=None, datasource_status=None):
        if history_index is not None and 0 <= history_index < len(self.chat_history):
            self.chat_history[history_index]["response"] = response
            self.chat_history[history_index]["datasource_status"] = datasource_status or ""

        self.output_area.delete("1.0", tk.END)
        self.output_area.insert(tk.END, response)
        references = self.extract_references(response)
        self.update_references_box(references)
        if datasource_status:
            self.latest_datasource_status = datasource_status
        self.update_datasource_box(self.latest_datasource_status)

    def on_history_select(self, event):
        selection = self.history_list.curselection()
        if not selection:
            return

        history_index = selection[0]
        if history_index >= len(self.chat_history):
            return

        question = self.chat_history[history_index]["question"]
        response = self.chat_history[history_index]["response"]
        datasource_status = self.chat_history[history_index].get("datasource_status", "")
        saved_filters = self.chat_history[history_index].get("filters", {})
        self.current_question = question
        self.recency_var.set(saved_filters.get("recency", "Any time"))
        self.content_type_var.set(saved_filters.get("content_type", "Mixed"))

        self.input_box.delete("1.0", tk.END)
        self.input_box.insert(tk.END, question)

        self.output_area.delete("1.0", tk.END)
        if response:
            self.output_area.insert(tk.END, response)
            references = self.extract_references(response)
            self.update_references_box(references)
            self.update_datasource_box(datasource_status or self.latest_datasource_status)
        else:
            self.output_area.insert(tk.END, "Still generating response for this question...")
            self.update_references_box([])
            self.update_datasource_box("Request still in progress for this history item.")

    def extract_references(self, response_text):
        if not response_text:
            return []

        markdown_urls = re.findall(r"\[[^\]]+\]\((https?://[^)\s]+)\)", response_text, flags=re.IGNORECASE)
        raw_urls = re.findall(
            r"(https?://[^\s<>\"]+|www\.[^\s<>\"]+|(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>\"]*)?)",
            response_text,
            flags=re.IGNORECASE
        )
        raw_urls = markdown_urls + raw_urls

        cleaned_urls = []
        seen = set()
        for raw_url in raw_urls:
            cleaned = raw_url.rstrip(".,;:!?)\"]}")
            if cleaned.lower().startswith("www.") or "://" not in cleaned:
                cleaned = f"https://{cleaned}"
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                cleaned_urls.append(cleaned)

        return cleaned_urls

    def update_references_box(self, references):
        self.references_box.config(state=tk.NORMAL, cursor="arrow")
        self.references_box.delete("1.0", tk.END)

        for tag_name in self.references_box.tag_names():
            if tag_name.startswith("ref_"):
                self.references_box.tag_delete(tag_name)

        if not references:
            self.references_box.insert(tk.END, "No references detected in this response.")
            self.references_box.config(state=tk.DISABLED)
            return

        for index, reference in enumerate(references, start=1):
            start_index = self.references_box.index(tk.END)
            self.references_box.insert(tk.END, f"{index}. {reference}\n")
            end_index = self.references_box.index(tk.END)
            tag_name = f"ref_{index}"
            self.references_box.tag_add(tag_name, start_index, end_index)
            self.references_box.tag_config(tag_name, foreground="#7FB3FF", underline=True)
            self.references_box.tag_bind(tag_name, "<Button-1>",
                                         lambda event, link=reference: self.open_reference(link))
            self.references_box.tag_bind(tag_name, "<Enter>",
                                         lambda event: self.references_box.config(cursor="hand2"))
            self.references_box.tag_bind(tag_name, "<Leave>",
                                         lambda event: self.references_box.config(cursor="arrow"))

        self.references_box.config(state=tk.DISABLED)

    def open_reference(self, url):
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            self.output_area.insert(tk.END, f"\n\nReference Open Error: {str(e)}")

    def update_datasource_box(self, status_text):
        self.datasource_box.config(state=tk.NORMAL)
        self.datasource_box.delete("1.0", tk.END)
        self.datasource_box.insert(tk.END, status_text)
        self.datasource_box.config(state=tk.DISABLED)

    def get_active_filters(self):
        return {
            "recency": self.recency_var.get(),
            "content_type": self.content_type_var.get()
        }

    def export_to_pdf(self):
        content = self.output_area.get("1.0", tk.END).strip()
        if not content:
            return
        question = self.current_question.strip() or self.input_box.get("1.0", tk.END).strip()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save as"
        )

        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(file_path)
            styles = getSampleStyleSheet()
            story = []

            # Title
            story.append(Paragraph("Polifine Legislative AI Report", styles["Title"]))
            story.append(Spacer(1, 12))

            # Question
            if question:
                story.append(Paragraph("<b>Question:</b>", styles["Heading3"]))
                story.append(Spacer(1, 6))
                story.append(Paragraph(question, styles["Normal"]))
                story.append(Spacer(1, 12))

            # Response
            story.append(Paragraph("<b>Response:</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))

            # Body text (split into paragraphs)
            for line in content.split("\n"):
                if line.strip():
                    story.append(Paragraph(line, styles["Normal"]))
                    story.append(Spacer(1, 8))

            doc.build(story)

        except Exception as e:
            self.output_area.insert(tk.END, f"\n\nPDF Export Error: {str(e)}")

    def call_deepseek(self, question, filters):
        deepseek_key = os.getenv("DeepSeek_API_KEY")
        if not deepseek_key:
            return "Error: API key not found in .env file.", "Datasource status unavailable (DeepSeek key missing)."

        source_context, datasource_status = self.fetch_data_source_context(question, filters)
        filter_summary = f"Recency={filters.get('recency', 'Any time')}, Content Type={filters.get('content_type', 'Mixed')}"
        enriched_question = (
            f"User question:\n{question}\n\n"
            f"Selected filters:\n{filter_summary}\n\n"
            f"Relevant datasource context (Congress.gov / Data.gov):\n"
            f"{source_context}\n\n"
            "Use the context if helpful, and still provide a clear answer."
        )

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system",
                 "content": "You are the Polifine Project AI assistant. Answer legislative questions professionally. "
                            "When possible, include 2-4 reputable source URLs as plain clickable links "
                            "(full https:// URLs)."},
                {"role": "user", "content": enriched_question}
            ],
            "temperature": 0.3
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"], datasource_status
        except Exception as e:
            return f"API Error: {str(e)}", datasource_status

    def fetch_data_source_context(self, question, filters):
        chunks = []
        status_lines = []
        filter_summary = f"Filters: Recency={filters.get('recency', 'Any time')}, Content Type={filters.get('content_type', 'Mixed')}"
        status_lines.append(filter_summary)

        congress_context, congress_status = self.fetch_congress_context(question, filters)
        if congress_context:
            chunks.append(congress_context)
        status_lines.append(congress_status)

        data_gov_context, data_gov_status = self.fetch_data_gov_context(question, filters)
        if data_gov_context:
            chunks.append(data_gov_context)
        status_lines.append(data_gov_status)

        if not chunks:
            return "No external datasource items were available at request time.", "\n".join(status_lines)

        return "\n\n".join(chunks), "\n".join(status_lines)

    def fetch_congress_context(self, question, filters):
        congress_key = os.getenv("Congress_API_KEY") or os.getenv("Congress.gov_API_KEY")
        if not congress_key:
            return "Congress.gov: API key not configured (set Congress_API_KEY in .env).", "Congress.gov: key missing."

        try:
            # Search by meaningful query terms first (title/number/committee context),
            # then fall back to recent bills if query results are sparse.
            stopwords = {
                "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it",
                "its", "of", "on", "or", "that", "the", "their", "there", "this", "to", "was", "were", "what",
                "when", "where", "which", "who", "why", "about", "latest", "status", "federal", "state", "with",
                "bill", "bills", "act", "acts", "committee", "please", "include", "source", "sources", "day"
            }
            terms = [term.lower() for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", question)]
            acronyms = [term for term in re.findall(r"\b[A-Z]{2,}\b", question) if len(term) <= 10]
            bill_ids = re.findall(r"\b(?:H\.?R\.?|S\.?|H\.?J\.?Res\.?|S\.?J\.?Res\.?)\s*\d+\b", question, flags=re.IGNORECASE)

            filtered = [term for term in terms if term not in stopwords]
            search_terms = []
            for token in acronyms + bill_ids + filtered:
                key = token.lower()
                if key not in search_terms:
                    search_terms.append(key)
            content_type = filters.get("content_type", "Mixed")
            if content_type == "Bills":
                search_terms.extend(["bill", "legislation"])
            elif content_type == "Resolutions":
                search_terms.extend(["resolution"])
            elif content_type == "Laws":
                search_terms.extend(["public law", "enacted"])

            search_terms = search_terms[:10]
            query = " ".join(search_terms) if search_terms else question.strip()

            recency = filters.get("recency", "Any time")
            if recency == "Last 30 days":
                query = f"{query} updated recently 30 days"
            elif recency == "Last 90 days":
                query = f"{query} updated recently 90 days"
            elif recency == "Current Congress":
                query = f"{query} current congress"

            bills = []
            for offset in (0, 50):
                response = requests.get(
                    "https://api.congress.gov/v3/bill",
                    params={
                        "format": "json",
                        "limit": 50,
                        "offset": offset,
                        "query": query,
                        "sort": "updateDate+desc",
                        "api_key": congress_key
                    },
                    timeout=20
                )
                response.raise_for_status()
                payload = response.json()
                page_bills = payload.get("bills", [])
                bills.extend(page_bills)
                if len(page_bills) < 50:
                    break

            # Query fallback: broaden to recent bills across two pages.
            if not bills:
                for offset in (0, 50):
                    response = requests.get(
                        "https://api.congress.gov/v3/bill",
                        params={
                            "format": "json",
                            "limit": 50,
                            "offset": offset,
                            "sort": "updateDate+desc",
                            "api_key": congress_key
                        },
                        timeout=20
                    )
                    response.raise_for_status()
                    payload = response.json()
                    page_bills = payload.get("bills", [])
                    bills.extend(page_bills)
                    if len(page_bills) < 50:
                        break

            if not bills:
                return "Congress.gov: No bill data returned.", f"Congress.gov: query='{query}', results=0."

            scored = []
            for bill in bills:
                title = (bill.get("title", "") or "").lower()
                bill_type = (bill.get("type", "") or "").lower()
                bill_number = str(bill.get("number", "") or "").lower()
                update_date = (bill.get("updateDate", "") or "").lower()
                combined = f"{title} {bill_type} {bill_number} {update_date}"
                score = sum(1 for term in search_terms if term in combined)
                scored.append((score, bill))

            scored.sort(key=lambda item: item[0], reverse=True)
            top_bills = [item[1] for item in scored[:3]]

            lines = [f"Congress.gov related bills (query='{query}'):"]
            for bill in top_bills:
                congress_num = bill.get("congress", "?")
                bill_type = bill.get("type", "?")
                bill_number = bill.get("number", "?")
                title = bill.get("title", "Untitled bill")
                bill_url = bill.get("url", "https://www.congress.gov")
                lines.append(f"- {bill_type} {bill_number} (Congress {congress_num}): {title} | {bill_url}")
            status = f"Congress.gov: query='{query}', fetched={len(bills)}, selected={len(top_bills)}."
            return "\n".join(lines), status
        except Exception as e:
            return f"Congress.gov datasource error: {str(e)}", f"Congress.gov error: {str(e)}"

    def fetch_data_gov_context(self, question, filters):
        data_gov_key = os.getenv("Data.gov_API_KEY")
        try:
            terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9-]{4,}", question)]
            recency = filters.get("recency", "Any time")
            content_type = filters.get("content_type", "Mixed")
            query_terms = terms[:8]
            if content_type == "Bills":
                query_terms.extend(["bill", "congress"])
            elif content_type == "Resolutions":
                query_terms.extend(["resolution"])
            elif content_type == "Laws":
                query_terms.extend(["law", "public"])
            if recency in {"Last 30 days", "Last 90 days"}:
                query_terms.append("recent")

            query = " ".join(query_terms) if query_terms else question.strip()
            headers = {}
            if data_gov_key:
                headers["X-Api-Key"] = data_gov_key

            response = requests.get(
                "https://catalog.data.gov/search",
                params={"q": query, "per_page": 25, "sort": "relevance"},
                headers=headers,
                timeout=20
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])

            if not results:
                return "Data.gov: No datasets returned.", f"Data.gov: query='{query}', results=0."

            scored_items = []
            for item in results:
                title = (item.get("title") or "").strip()
                notes = (item.get("notes") or "").strip()
                page_url = (item.get("url") or "").strip()
                if not page_url:
                    page_url = f"https://catalog.data.gov/dataset/{item.get('name', '')}".rstrip("/")
                content = f"{title} {notes}".lower()
                score = sum(1 for term in terms if term in content)
                scored_items.append((score, title, page_url))

            scored_items.sort(key=lambda row: row[0], reverse=True)
            top_items = scored_items[:3]

            lines = ["Data.gov related datasets:"]
            for _, title, link in top_items:
                label = title if title else "Data.gov dataset"
                lines.append(f"- {label} | {link}")
            status = f"Data.gov: query='{query}', fetched={len(results)}, selected={len(top_items)}."
            if not data_gov_key:
                status += " (Data.gov_API_KEY not set; continuing with public catalog access)"
            return "\n".join(lines), status
        except Exception as e:
            return f"Data.gov datasource error: {str(e)}", f"Data.gov error: {str(e)}"


if __name__ == "__main__":
    root = tk.Tk()
    app = LegislativeAIApp(root)
    root.mainloop()
