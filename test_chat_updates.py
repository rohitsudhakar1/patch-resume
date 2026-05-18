"""
Comprehensive test for chat-to-update functionality
Tests all 3 operations: add, remove, replace
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_test(message):
    """Print test message with formatting"""
    print(f"\n{'='*60}")
    print(f"TEST: {message}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"📝 {message}")

def create_sample_resume():
    """Create a sample resume LaTeX content"""
    return r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}

\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

\begin{document}

\begin{center}
\textbf{John Doe}

Email: john.doe@email.com | Phone: (555) 123-4567 | Location: New York, NY
\end{center}

\section*{Work Experience}

\textbf{Software Engineer} | Tech Company | Jan 2020 - Present

\begin{itemize}
\item Developed web applications using React and TypeScript
\item Collaborated with cross-functional teams
\item Improved system performance by 30\%
\end{itemize}

\textbf{Junior Developer} | Startup Inc | Jun 2018 - Dec 2019

\begin{itemize}
\item Built RESTful APIs using Python and Flask
\item Worked on database optimization
\end{itemize}

\section*{Education}

\textbf{Bachelor of Science in Computer Science}

University of Example | 2014 - 2018 | GPA: 3.8

\section*{Skills}

Python, JavaScript, React, TypeScript, SQL, Git

\end{document}
"""

def test_chat_update(project_id, resume_tex, instruction, expected_in_result):
    """Test a chat update and verify the result"""
    print_info(f"Sending instruction: '{instruction}'")

    # Send chat message
    response = requests.post(
        f"{BASE_URL}/llm/chat",
        json={
            "message": instruction,
            "chat_history": [],
            "current_resume": resume_tex,
            "context": {
                "has_resume": True,
                "resume_length": len(resume_tex),
                "project_id": project_id
            }
        }
    )

    if response.status_code != 200:
        print_error(f"Chat request failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

    data = response.json()
    print_success(f"AI Response: {data['response'][:100]}...")

    # Check if it's a resume update
    if not data.get('is_resume_update'):
        print_error("Response is not marked as a resume update")
        return None

    print_success("Response is marked as a resume update")

    # Check if resume_data exists
    if not data.get('resume_data'):
        print_error("No resume_data in response")
        return None

    updated_tex = data['resume_data']
    print_success(f"Received updated resume (length: {len(updated_tex)})")

    # Verify the expected content is in the result
    if expected_in_result:
        if expected_in_result in updated_tex:
            print_success(f"Found expected content: '{expected_in_result}'")
        else:
            print_error(f"Expected content not found: '{expected_in_result}'")
            print_info(f"Resume preview: {updated_tex[:500]}...")
            return None

    return updated_tex

def test_pdf_generation(project_id):
    """Test PDF generation for a project"""
    print_info(f"Testing PDF generation for project {project_id}")

    response = requests.get(f"{BASE_URL}/artifact/pdf/{project_id}")

    if response.status_code != 200:
        print_error(f"PDF generation failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False

    if response.headers.get('content-type') != 'application/pdf':
        print_error(f"Response is not a PDF: {response.headers.get('content-type')}")
        return False

    print_success(f"PDF generated successfully (size: {len(response.content)} bytes)")
    return True

def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE CHAT UPDATE TEST SUITE")
    print("="*60)

    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print_error("Backend health check failed")
            return False
        print_success("Backend is running")
    except Exception as e:
        print_error(f"Cannot connect to backend: {e}")
        return False

    # Create a project with sample resume
    print_test("Creating Project")
    project_id = f"test_project_{int(time.time())}"
    initial_resume = create_sample_resume()

    response = requests.post(
        f"{BASE_URL}/project/recreate",
        json={
            "id": project_id,
            "resume_tex": initial_resume
        }
    )

    if response.status_code != 200:
        print_error(f"Failed to create project: {response.status_code}")
        return False

    print_success(f"Created project: {project_id}")

    # Test 1: Replace - Name change
    print_test("Test 1: Replace - Name Change")
    updated_resume = test_chat_update(
        project_id,
        initial_resume,
        "change name to Jane Smith",
        "Jane Smith"
    )

    if not updated_resume:
        print_error("Test 1 FAILED")
        return False

    print_success("Test 1 PASSED - Name changed successfully")

    # Verify PDF can be generated with updated content
    if not test_pdf_generation(project_id):
        print_error("PDF generation failed after name change")
        return False

    # Test 2: Remove - Remove first experience
    print_test("Test 2: Remove - Remove First Experience")
    updated_resume = test_chat_update(
        project_id,
        updated_resume,
        "remove the first work experience entry",
        None  # We'll check that "Tech Company" is gone
    )

    if not updated_resume:
        print_error("Test 2 FAILED")
        return False

    # Check that "Tech Company" is no longer in the resume
    if "Tech Company" in updated_resume:
        print_error("First experience was not removed - 'Tech Company' still present")
        return False

    print_success("Test 2 PASSED - First experience removed successfully")

    # Verify PDF can be generated
    if not test_pdf_generation(project_id):
        print_error("PDF generation failed after removing experience")
        return False

    # Test 3: Add - Add a new skill
    print_test("Test 3: Add - Add New Skill")
    updated_resume = test_chat_update(
        project_id,
        updated_resume,
        "add Kubernetes to my skills",
        "Kubernetes"
    )

    if not updated_resume:
        print_error("Test 3 FAILED")
        return False

    print_success("Test 3 PASSED - Skill added successfully")

    # Verify PDF can be generated
    if not test_pdf_generation(project_id):
        print_error("PDF generation failed after adding skill")
        return False

    # Final summary
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✅")
    print("="*60)
    print("\nSummary:")
    print("✅ Replace operation (name change) - PASSED")
    print("✅ Remove operation (delete experience) - PASSED")
    print("✅ Add operation (add skill) - PASSED")
    print("✅ PDF generation after each update - PASSED")
    print("\nThe chat-to-update functionality is working correctly!")
    print("="*60 + "\n")

    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)