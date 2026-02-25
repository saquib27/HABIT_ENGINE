document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    const emailInput = document.getElementById("email");
    const passInput = document.getElementById("password");
    const errorMsg = document.getElementById("passwordError");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = emailInput.value.trim();
        const password = passInput.value;

        clearError();

        try {
            await auth.signInWithEmailAndPassword(email, password);

            alert("Login successful! Welcome back");
            form.reset();
            window.location.href = "dashboard.html";

        } catch (error) {
            showError("Incorrect email or password.");
        }
    });

    passInput.addEventListener("input", clearError);
    emailInput.addEventListener("input", clearError);

    function showError(message) {
        passInput.classList.add("input-error");
        errorMsg.textContent = message;
        errorMsg.classList.add("visible");
        passInput.focus();
    }

    function clearError() {
        passInput.classList.remove("input-error");
        errorMsg.classList.remove("visible");
        errorMsg.textContent = "";
    }
});