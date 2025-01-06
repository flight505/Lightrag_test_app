import fitz

# Create a new PDF document
doc = fitz.open()
page = doc.new_page()

# Add some test content with lists
text = """# Sample Academic Paper

## Abstract
This is a sample academic paper created for testing purposes.

## Introduction
The introduction provides context and background information.

## Methods
Our methodology involves several key steps:
- Data collection and preprocessing
- Model development and training
- Evaluation and testing

## Results
The results show significant improvements:
1. Accuracy increased by 25%
2. Processing time reduced by 50%
3. Memory usage optimized by 30%

## Conclusion
In conclusion, we have demonstrated...

## References
1. Smith, J. (2023). A Study of Something
2. Jones, M. (2022). Another Important Paper
"""

# Insert the text
page.insert_text((50, 50), text, fontsize=12)

# Save the PDF
doc.save("tests/data/sample.pdf")
doc.close()

print("Test PDF created successfully") 