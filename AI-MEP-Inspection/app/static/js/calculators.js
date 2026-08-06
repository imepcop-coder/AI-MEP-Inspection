document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#calculatorForm") || document.querySelector('form');

  if (form) {
    const resetButton = document.querySelector("#resetCalculator");
    const exportPdfButton = document.querySelector("#exportPdf");
    const exportExcelButton = document.querySelector("#exportExcel");

    // Utility: set error
    function setFieldError(input, message) {
      const id = input.id || input.name;
      const errorEl = document.getElementById(`error-${id}`);
      const helperId = `helper-${id}`;
      const errorId = `error-${id}`;

      if (message) {
        input.classList.add('is-invalid');
        input.setAttribute('aria-invalid', 'true');
        // ensure both helper + error are referenced
        input.setAttribute('aria-describedby', `${helperId} ${errorId}`);
        if (errorEl) {
          errorEl.innerHTML = `<i class="bi bi-exclamation-circle-fill me-1"></i>${message}`;
        }
      } else {
        input.classList.remove('is-invalid');
        input.setAttribute('aria-invalid', 'false');
        // only helper referenced when no error
        input.setAttribute('aria-describedby', helperId);
        if (errorEl) {
          errorEl.textContent = '';
        }
      }
    }

    // Display a batch of field errors (errors is an object mapping fieldName->message)
    function showFieldErrors(errors) {
      if (!errors || typeof errors !== 'object') return;
      let firstEl = null;
      Object.keys(errors).forEach((key) => {
        const el = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
        if (el) {
          setFieldError(el, errors[key]);
          if (!firstEl) firstEl = el;
        }
      });
      if (firstEl) {
        firstEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        try { firstEl.focus({ preventScroll: true }); } catch (e) { firstEl.focus(); }
      }
    }

    // Validate a single field element. Returns true if valid.
    function validateField(el) {
      const required = el.dataset.required === '1';
      const type = el.type || el.tagName.toLowerCase();
      const value = el.value?.toString().trim();
      const id = el.id || el.name;

      // For selects, ensure value present if required
      if (el.tagName.toLowerCase() === 'select') {
        if (required && (!value || value === '')) {
          setFieldError(el, `${id.replace(/_/g, ' ')} is required.`);
          return false;
        }
        setFieldError(el, '');
        return true;
      }

      if (required && !value) {
        setFieldError(el, `${id.replace(/_/g, ' ')} is required.`);
        return false;
      }

      if (!value) {
        // not required and empty — clear errors
        setFieldError(el, '');
        return true;
      }

      // If input type is number or has data-step -> validate numeric
      const step = el.dataset.step;
      const min = el.dataset.min !== undefined ? parseFloat(el.dataset.min) : null;
      const max = el.dataset.max !== undefined ? parseFloat(el.dataset.max) : null;
      const decimalsAllowed = el.dataset.decimals === '1';

      if (type === 'number' || step || el.type === 'number') {
        const num = Number(value);
        if (Number.isNaN(num)) {
          setFieldError(el, `${id.replace(/_/g, ' ')} must be a number.`);
          return false;
        }
        if (!isFinite(num)) {
          setFieldError(el, `${id.replace(/_/g, ' ')} must be a finite number.`);
          return false;
        }
        if (min !== null && num < min) {
          setFieldError(el, `${id.replace(/_/g, ' ')} must be greater than or equal to ${min}.`);
          return false;
        }
        if (max !== null && num > max) {
          setFieldError(el, `${id.replace(/_/g, ' ')} must be less than or equal to ${max}.`);
          return false;
        }
        if (!decimalsAllowed) {
          // enforce whole numbers
          if (!Number.isInteger(num)) {
            setFieldError(el, `${id.replace(/_/g, ' ')} must be a whole number.`);
            return false;
          }
        }
      }

      // passed all checks
      setFieldError(el, '');
      return true;
    }

    // attach listeners to inputs/selects for real-time validation
    const inputs = Array.from(form.querySelectorAll('input, select, textarea'));
    inputs.forEach((el) => {
      // ignore buttons/submit
      if (el.type === 'submit' || el.type === 'button' || el.disabled) return;

      // on input validate lightly
      el.addEventListener('input', () => {
        validateField(el);
      });
      // on blur validate thoroughly
      el.addEventListener('blur', () => {
        validateField(el);
      });
    });

    resetButton?.addEventListener("click", () => {
      form.reset();
      document.querySelectorAll('.field-error').forEach((el) => el.textContent = '');
      document.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
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

    // intercept form submit to run validation
    form.addEventListener('submit', (e) => {
      const allInputs = Array.from(form.querySelectorAll('input, select, textarea'))
        .filter(el => !(el.type === 'submit' || el.type === 'button'));

      let firstInvalid = null;
      for (const el of allInputs) {
        const ok = validateField(el);
        if (!ok && !firstInvalid) firstInvalid = el;
      }

      if (firstInvalid) {
        e.preventDefault();
        // scroll and focus
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstInvalid.focus({ preventScroll: true });
      }
    });

    const handleExport = async (exportUrl, filename) => {
      const formData = new FormData(form);

      try {
        const response = await fetch(exportUrl, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
            // Try to parse structured JSON errors
            let parsed = null;
            try {
              parsed = await response.json();
            } catch (e) {
              // not JSON
              const text = await response.text();
              throw new Error(text || 'Export failed.');
            }

            if (parsed && parsed.errors) {
              // display field-specific errors
              showFieldErrors(parsed.errors);
              throw new Error('Validation failed. Please correct the highlighted fields.');
            }

            // fallback
            throw new Error(parsed.error || 'Export failed.');
          }

          const blob = await response.blob();
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } catch (error) {
          // friendly inline error
          const alertBox = document.createElement('div');
          alertBox.className = 'alert alert-danger mt-3';
          alertBox.textContent = `${filename.split('.').pop().toUpperCase()} export failed: ${error.message}`;
          form.prepend(alertBox);
          setTimeout(() => alertBox.remove(), 8000);
        }
    };

    if (exportPdfButton) {
      exportPdfButton.addEventListener('click', async (e) => {
        // If no result on page, prompt user to calculate first
        if (!document.querySelector('.result-value')) {
          // show friendly UI error rather than alert
          const alertBox = document.createElement('div');
          alertBox.className = 'alert alert-warning mt-3';
          alertBox.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>Please run the calculation first. The PDF/Excel report uses the calculated results and input values.';
          form.prepend(alertBox);
          setTimeout(() => alertBox.remove(), 6000);
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
          const alertBox = document.createElement('div');
          alertBox.className = 'alert alert-warning mt-3';
          alertBox.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>Please run the calculation first. The PDF/Excel report uses the calculated results and input values.';
          form.prepend(alertBox);
          setTimeout(() => alertBox.remove(), 6000);
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