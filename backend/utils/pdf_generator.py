import os
from fpdf import FPDF
from datetime import datetime

class OutpassPDF(FPDF):
    def header(self):
        # Logo placeholder
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(16, 185, 129) # Primary color
        self.cell(0, 10, 'SMART OUTPASS SYSTEM', ln=True, align='C')
        self.set_font('helvetica', '', 10)
        self.set_text_color(100, 116, 139) # Text muted
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%d %b %Y, %I:%M %p")}', ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()} / {{nb}}', align='C')

def generate_staff_monthly_report(staff_name, month_name, year, records):
    pdf = OutpassPDF(orientation='L') # Landscape
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Title
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, f'Staff Outpass History - {month_name} {year}', ln=True)
    
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'Advisor: {staff_name}', ln=True)
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font('helvetica', 'B', 10)
    
    cols = [
        ('Student', 50),
        ('Reg No', 30),
        ('Date', 25),
        ('Exit Time', 35),
        ('Entry Time', 35),
        ('Reason', 65),
        ('Status', 30)
    ]
    
    for col_name, width in cols:
        pdf.cell(width, 10, col_name, border=1, align='C', fill=True)
    pdf.ln()
    
    # Table Content
    pdf.set_font('helvetica', '', 9)
    for row in records:
        if pdf.get_y() > 180: # Adjust for landscape
            pdf.add_page()
        
        pdf.cell(50, 10, str(row['student_name']), border=1)
        pdf.cell(30, 10, str(row['registration_no']), border=1, align='C')
        pdf.cell(25, 10, str(row['out_date']), border=1, align='C')
        
        # Exit/Entry times
        exit_time = row.get('actual_exit_time')
        entry_time = row.get('actual_entry_time')
        
        # Helper to format time if it's a datetime object
        def fmt_t(t):
            if not t: return '-'
            if isinstance(t, str): return t
            return t.strftime('%I:%M %p')

        pdf.cell(35, 10, fmt_t(exit_time), border=1, align='C')
        pdf.cell(35, 10, fmt_t(entry_time), border=1, align='C')
        
        # Multiline reason
        reason = str(row['reason'])
        if len(reason) > 40:
            reason = reason[:37] + '...'
        pdf.cell(65, 10, reason, border=1)
        
        pdf.cell(30, 10, str(row['final_status']).capitalize(), border=1, align='C')
        pdf.ln()
        
    return pdf.output()

def generate_hod_monthly_report(dept_name, month_name, year, records_by_year):
    pdf = OutpassPDF(orientation='L') # Landscape
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Title
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, f'Departmental Outpass History - {month_name} {year}', ln=True)
    
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'Department: {dept_name}', ln=True)
    pdf.ln(10)
    
    for academic_year, records in records_by_year.items():
        if not records:
            continue
            
        pdf.set_font('helvetica', 'B', 14)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 10, f'{academic_year} Students', ln=True)
        pdf.ln(2)
        
        # Table Header
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font('helvetica', 'B', 9)
        
        cols = [
            ('Student', 45),
            ('Reg No', 25),
            ('Date', 22),
            ('Exit', 30),
            ('Entry', 30),
            ('Reason', 50),
            ('Advisor', 35),
            ('Status', 20)
        ]
        
        for col_name, width in cols:
            pdf.cell(width, 8, col_name, border=1, align='C', fill=True)
        pdf.ln()
        
        # Table Content
        pdf.set_font('helvetica', '', 8)
        for row in records:
            if pdf.get_y() > 185:
                pdf.add_page()
            
            pdf.cell(45, 8, str(row['student_name']), border=1)
            pdf.cell(25, 8, str(row['registration_no']), border=1, align='C')
            pdf.cell(22, 8, str(row['out_date']), border=1, align='C')
            
            # Helper to format time
            def fmt_t(t):
                if not t: return '-'
                if isinstance(t, str): return t
                return t.strftime('%I:%M %p')

            pdf.cell(30, 8, fmt_t(row.get('actual_exit_time')), border=1, align='C')
            pdf.cell(30, 8, fmt_t(row.get('actual_entry_time')), border=1, align='C')
            
            reason = str(row['reason'])
            if len(reason) > 30:
                reason = reason[:27] + '...'
            pdf.cell(50, 8, reason, border=1)
            
            pdf.cell(35, 8, str(row['advisor_name']) if 'advisor_name' in row else 'N/A', border=1)
            pdf.cell(20, 8, str(row['final_status']).capitalize(), border=1, align='C')
            pdf.ln()
        
        pdf.ln(10)
        
    return pdf.output()
