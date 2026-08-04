document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#calculatorForm");

  if (form) {
    const resetButton = document.querySelector("#resetCalculator");
    const exportPdfButton = document.querySelector("#exportPdf");
    const exportExcelButton = document.querySelector("#exportExcel");

    resetButton?.addEventListener("click", () => {
      form.reset();
      document.querySelectorAll(".field-error").forEach((el) => {
        el.textContent = "";
      });
      document.querySelectorAll(".is-invalid").forEach((el) => {
        el.classList.remove("is-invalid");
      });
      const resultCard = document.querySelector(".result-value");
      if (resultCard) {
        resultCard.textContent = "";
      }
      const placeholder = document.querySelector(".result-placeholder");
      if (placeholder) {
        placeholder.style.display = "block";
      }
    });

    const hasResult = !!document.querySelector('.result-value');

    // Disable export buttons until a calculation has been performed
    if (!hasResult) {
      if (exportPdfButton) {
        exportPdfButton.disabled = true;
        exportPdfButton.title = 'Calculate first to enable PDF export';
        exportPdfButton.classList.add('disabled');
      }
      if (exportExcelButton) {
        exportExcelButton.disabled = true;
        exportExcelButton.title = 'Calculate first to enable Excel export';
        exportExcelButton.classList.add('disabled');
      }
    }

    const handleExport = async (exportUrl, filename) => {
      const formData = new FormData(form);

      try {
        const response = await fetch(exportUrl, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Export failed.');
        }

        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } catch (error) {
        alert(`${filename.split('.').pop().toUpperCase()} export failed: ${error.message}`);
      }
    };

    if (exportPdfButton) {
      exportPdfButton.addEventListener('click', async (e) => {
        // If no result on page, prompt user to calculate first
        if (!document.querySelector('.result-value')) {
          alert('Please run the calculation first. The PDF/Excel report uses the calculated results and input values.');
          return;
        }
        const calculatorTitle = document.querySelector('.calculator-panel h2')?.textContent || 'calculator';
        const filename = `${calculatorTitle.replace(/\s+/g, '_')}.pdf`;
        const exportUrl = `${window.location.pathname}/export_pdf`;
        await handleExport(exportUrl, filename);
      });
    }

    if (exportExcelButton) {
      exportExcelButton.addEventListener('click', async (e) => {
        if (!document.querySelector('.result-value')) {
          alert('Please run the calculation first. The PDF/Excel report uses the calculated results and input values.');
          return;
        }
        const calculatorTitle = document.querySelector('.calculator-panel h2')?.textContent || 'calculator';
        const filename = `${calculatorTitle.replace(/\s+/g, '_')}.xlsx`;
        const exportUrl = `${window.location.pathname}/export_excel`;
        await handleExport(exportUrl, filename);
      });
    }
  }
});
