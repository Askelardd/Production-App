# 📦 Sistema de Gestão de Caixas e Esferas - Toma Tools

## 📖 Introdução
Este projeto foi desenvolvido com o objetivo de **organizar e otimizar o setor de Produção, Q-Office, Administração e Comercial da empresa Toma Tools**, garantindo melhor controle sobre **onde estão e como estão as caixas, fieiras e encomendas da empresa**.

---

## 📑 Índice
- [Introdução](#-introdução)
- [Funcionalidades](#-funcionalidades)
- [Habilidades Adquiridas](#-habilidades-adquiridas)
- [Como Executar](#-como-executar)
- [Contribuindo](#-contribuindo)
- [Créditos e Licença](#-créditos-e-licença)

---

## ✅ Funcionalidades
- **Login individual** para cada funcionário, com permissões específicas.
- **Leitura de QR Code** para identificar caixas e importar informações.
- **Criação automática de campos** para preenchimento de dados das esferas.
- **Atribuição de trabalhos** a cada esfera e associação de trabalhadores a tarefas.
- **Gestão avançada**, permitindo:
  - Criar esferas partidas
  - Alterar diâmetro
  - Mover caixas para outros setores
- **Exportação de dados para Excel** para relatórios e análise.
- **Criação/Edição de encomendas** para uma melhor gestão das encomendas e saber onde elas estão localizadas

---

## 🛠 Habilidades Adquiridas
Durante o desenvolvimento deste projeto, aprendi e aprofundei conhecimentos sobre:
- **Django** (estrutura e organização de projetos)
- **Tailwind CSS** para estilização
- Melhores práticas de desenvolvimento web full stack

---

## ▶ Como Executar

### ✅ Pré-requisitos
- **Python 3.x** instalado
- **Pip** para gerenciamento de pacotes
- **Ambiente virtual** (recomendado)

### ✅ Passos para execução local
1. Clone este repositório:
    ```bash
    git clone https://github.com/teu-repo.git
    cd teu-repo
    ```
2. Crie um ambiente virtual:
    ```bash
    python -m venv venv
    ```
3. Ative o ambiente virtual:
    - **Windows:**
      ```bash
      venv\Scripts\activate
      ```
    - **Linux/Mac:**
      ```bash
      source venv/bin/activate
      ```
4. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
5. Execute as migrações:
    ```bash
    python manage.py migrate
    ```
6. Inicie o servidor:
    ```bash
    python manage.py runserver
    ```

### ✅ Acesso
- Funcionários da Toma Tools: **Acesse pelo servidor interno**
- Desenvolvimento local: **http://127.0.0.1:8000/**

---
## 🖼️ Algumas imagens do Projeto

### 🌐 Login Page
<img src="https://github.com/user-attachments/assets/823c36c3-243f-49d3-8ba0-6f7af6711467" alt="Página de Login" width="100%" />

### 🌀 Dies Page
<img src="https://github.com/user-attachments/assets/5d85fc5f-df4f-465b-8d39-56a35351839d" alt="Página de Gerenciamento de Esferas" width="100%" />

### 📷 Scan Box
<img src="https://github.com/user-attachments/assets/da3306cc-6d71-41a2-a304-9ac3237056a0" alt="Página de Leitura de QR Code" width="100%" />


---
## 🤝 Contribuindo
Este projeto foi desenvolvido integralmente por mim (front-end e back-end).  
Caso queira contribuir ou sugerir melhorias, sinta-se à vontade para:
- Criar um **pull request**
- Abrir uma **issue** no repositório

---

## 📜 Créditos e Licença
© 2025 Toma Tools. Todos os direitos reservados.

---

## 💻 Tecnologias Utilizadas
- **Django** (Backend)
- **Tailwind CSS** (Frontend)
- **Python**
- **HTML5 / CSS3 / JavaScript**
- **SQLite** (Banco de dados padrão do Django)

---

<!-- Aqui você pode adicionar screenshots ou GIFs mostrando a aplicação -->
