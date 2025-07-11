

function basicKnowledge() {
let nome = "Andre";
let idade = 25;
let cidade = "Esposende";

console.log("Ola o meu nome é" + nome +" e tenho " + idade + " anos, e moro em " + cidade);
}

function somaSimples()
{
let num1 = 5;
let num2 = 10;
let resultado = num1 + num2;
console.log("A soma de " + num1 + " e " + num2 + " é igual a " + resultado);
}

function converterValores()
{
let valorString = "123";
let valorNumero = parseInt(valorString); // ou parseFloat(valorString) para números decimais
console.log("O valor convertido de string para número é: " + valorNumero);
}

function condicions()
{
let idade = 18;
if (idade >= 18) {
    console.log("Podes entrar");
} else {
    console.log("Nao podes entrar");
}
}

function loops()
{
    for(let i = 0; i < 10; i++)
    {
        console.log("O valor de i é: " + i);
    }

    let frutas = ["maçã", "banana", "laranja"];

    for(let i = 0; i < frutas.length; i++)
    {
        console.log("Fruta: " + frutas[i]);
    }

    // ou 

    for(let fruta of frutas)
    {
        console.log("Fruta: " + fruta);
    }

    for(let i= 0; i < 50; i++)
    {
        if(i % 2 === 0)
        {
            console.log("Numeros pares: " + i);
        }
    }
}

function boasVindas()
{
    let nome = prompt("Qual é o teu nome?");
    let hora = new Date().getHours();

    if (hora < 12) {
        console.log("Bom dia, " + nome + "!");
    }
    else if (hora < 18) {
        console.log("Boa tarde, " + nome + "!");
    } else {
        console.log("Boa noite, " + nome + "!");
    }
}

function objects()
{
    let pessoas = [{ nome: "Andre", idade: 25, profissao: "Programador" },
        { nome: "Maria", idade: 30, profissao: "Designer" }];
                
    for (let pessoa of pessoas) {
        console.log("Nome: " + pessoa.nome + ", Idade: " + pessoa.idade + ", Profissão: " + pessoa.profissao);
    }
}

function listaTarefas()
{
    let tarefas = ["Estudar JavaScript", "Fazer exercício", "Ler um livro"];

    let newTarefa = prompt("Adicione uma nova tarefa:");
    tarefas.push(newTarefa);

    console.log("Lista de Tarefas:");
    for (let i = 0; i < tarefas.length; i++) {
        console.log((i + 1) + ". " + tarefas[i]);
    }
}

function calculadora()
{
    let num1 = parseFloat(prompt("Digite o primeiro número:"));
    let num2 = parseFloat(prompt("Digite o segundo número:"));
    switch (prompt("Escolha uma operação: +, -, *, /")) {
        case "+":
            console.log("Resultado: " + (num1 + num2));
            break;
        case "-":
            console.log("Resultado: " + (num1 - num2));
            break;
        case "*":
            console.log("Resultado: " + (num1 * num2));
            break;
        case "/":
            if (num2 !== 0) {
                console.log("Resultado: " + (num1 / num2));
            } else {
                console.log("Erro: Divisão por zero não é permitida.");
            }
            break;
        default:
            console.log("Operação inválida.");
            break;
        
    }
}

function maiorNumero()
{
    let numeros = [];

    let qnt = parseInt(prompt("Quantos números queres inserir?"));

    for (let i = 0; i < qnt; i++) {
        let numero = parseFloat(prompt("Digite o número " + (i + 1) + ":"));
        numeros.push(numero);
    }
    let maior = numeros[0];
    for (let i = 1; i < numeros.length; i++) {
        if (numeros[i] > maior) {
            maior = numeros[i];
        }
    }
    console.log("O maior número é: " + maior);
}

function palindromo()
{
    let palavra = prompt("Digite uma palavra ou frase:");
    // Remover espaços e converter para minúsculas
    palavra = palavra.replace(/\s+/g, '').toLowerCase();
    // Verificar se é um palíndromo
    let ehPalindromo = palavra === palavra.split('').reverse().join('');
    if (ehPalindromo) {
        console.log("A palavra ou frase é um palíndromo.");
    } else {
        console.log("A palavra ou frase não é um palíndromo.");
    }
}

function Fibonacci()
{
    let n = parseInt(prompt("Quantos termos da sequência de Fibonacci você deseja?"));
    let fib = [0, 1];
    for (let i = 2; i < n; i++) {
        fib[i] = fib[i - 1] + fib[i - 2];
    }
    console.log("Sequência de Fibonacci: " + fib.slice(0, n).join(', '));
}
