function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeOpen = document.getElementById('eye-open');
    const eyeClosed = document.getElementById('eye-closed');

    const isPassword = passwordInput.type === 'password';
    passwordInput.type = isPassword ? 'text' : 'password';
    eyeOpen.classList.toggle('hidden', !isPassword);
    eyeClosed.classList.toggle('hidden', isPassword);
}


// Validação do campo first_name
function validateFirstName() {
    const firstNameInput = document.getElementById('first_name');
    const errorDiv = document.getElementById('first_name_error');
    const value = firstNameInput.value.trim();

    if (value.length === 0) {
        showError(errorDiv, 'O nome é obrigatório');
        return false;
    } else if (value.length > 30) {
        showError(errorDiv, 'O nome não pode ter mais de 30 caracteres');
        return false;
    } else {
        hideError(errorDiv);
        return true;
    }
}

// Validação do campo password
function validatePassword() {
    const passwordInput = document.getElementById('password');
    const errorDiv = document.getElementById('password_error');
    const value = passwordInput.value;

    if (value.length === 0) {
        showError(errorDiv, 'A palavra-passe é obrigatória');
        return false;
    } else if (value.length < 6) {
        showError(errorDiv, 'A palavra-passe deve ter pelo menos 6 caracteres');
        return false;
    } else if (value.length > 100) {
        showError(errorDiv, 'A palavra-passe não pode ter mais de 100 caracteres');
        return false;
    } else {
        hideError(errorDiv);
        return true;
    }
}

// Função para mostrar erro
function showError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Função para esconder erro
function hideError(errorDiv) {
    errorDiv.classList.add('hidden');
}

// Validação completa do formulário
function validateForm() {
    const isFirstNameValid = validateFirstName();
    const isPasswordValid = validatePassword();
    
    return isFirstNameValid && isPasswordValid;
}

// Adicionar event listeners para validação em tempo real
document.getElementById('first_name').addEventListener('input', function() {
    if (this.value.length > 0) {
        validateFirstName();
    }
});

document.getElementById('password').addEventListener('input', function() {
    if (this.value.length > 0) {
        validatePassword();
    }
});
