document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("signupForm");
    const nameInput = document.getElementById("name");
    const phoneInput = document.getElementById("phone");
    const emailInput = document.getElementById("email");
    const passInput = document.getElementById("password");
    const confirmInput = document.getElementById("confirm_password");

    const strengthBar = document.getElementById("strengthBar");
    const strengthLabel = document.getElementById("strengthLabel");

    passInput.addEventListener("input", () => {
        const score = getPasswordStrength(passInput.value);

        const levels = [
            { width: "0%", color: "transparent", text: "" },
            { width: "25%", color: "#f87171", text: "Weak" },
            { width: "50%", color: "#f59e0b", text: "Fair" },
            { width: "75%", color: "#a78bfa", text: "Good" },
            { width: "100%", color: "#34d399", text: "Strong" },
        ];

        const lvl = levels[score];

        strengthBar.style.width = lvl.width;
        strengthBar.style.background = lvl.color;
        strengthLabel.textContent = lvl.text;
        strengthLabel.style.color = score > 0 ? lvl.color : "rgba(255,255,255,0.4)";

        if (confirmInput.value) validateConfirm();
    });

    confirmInput.addEventListener("input", validateConfirm);

    [nameInput, phoneInput, emailInput, passInput, confirmInput].forEach(input => {
        input.addEventListener("input", () => clearError(input));
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        let valid = true;

        if (!nameInput.value.trim() || nameInput.value.trim().split(/\s+/).length < 2) {
            showError(nameInput, "Please enter your full name (first & last).");
            valid = false;
        }

        const phonePattern = /^\+?[0-9]{7,15}$/;
        if (!phonePattern.test(phoneInput.value.trim())) {
            showError(phoneInput, "Enter a valid phone number (digits only, 7–15 chars).");
            valid = false;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
            showError(emailInput, "Please enter a valid email address.");
            valid = false;
        }

        if (getPasswordStrength(passInput.value) < 2) {
            showError(passInput, "Password is too weak. Use at least 8 characters.");
            valid = false;
        }

        if (passInput.value !== confirmInput.value) {
            showError(confirmInput, "Passwords do not match.");
            valid = false;
        }

        if (!valid) return;

        try {
            const cred = await auth.createUserWithEmailAndPassword(
                emailInput.value.trim(),
                passInput.value
            );

            await db.collection("users").doc(cred.user.uid).set({
                name: nameInput.value.trim(),
                phone: phoneInput.value.trim(),
                email: emailInput.value.trim(),
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            });

            alert("Account created successfully! Welcome");

            form.reset();
            strengthBar.style.width = "0%";
            strengthLabel.textContent = "";

            window.location.href = "login.html";

        } catch (error) {
            alert(error.message);
        }
    });

    function getPasswordStrength(pw) {
        if (!pw) return 0;
        let score = 0;
        if (pw.length >= 8) score++;
        if (/[A-Z]/.test(pw)) score++;
        if (/[0-9]/.test(pw)) score++;
        if (/[^A-Za-z0-9]/.test(pw)) score++;
        return score;
    }

    function validateConfirm() {
        if (!confirmInput.value) return;

        if (passInput.value !== confirmInput.value) {
            showError(confirmInput, "Passwords do not match.");
        } else {
            clearError(confirmInput);
            showSuccess(confirmInput);
        }
    }

    function showError(input, message) {
        input.classList.remove("input-success");
        input.classList.add("input-error");

        const msg = input.parentElement.querySelector(".field-message");
        if (msg) {
            msg.textContent = message;
            msg.className = "field-message error visible";
        }
    }

    function showSuccess(input) {
        input.classList.remove("input-error");
        input.classList.add("input-success");

        const msg = input.parentElement.querySelector(".field-message");
        if (msg) {
            msg.textContent = "Looks good!";
            msg.className = "field-message success visible";
        }
    }

    function clearError(input) {
        input.classList.remove("input-error", "input-success");

        const msg = input.parentElement.querySelector(".field-message");
        if (msg) msg.classList.remove("visible");
    }
});