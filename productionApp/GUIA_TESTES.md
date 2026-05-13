# ✅ Guia de Testes - Tratamento de Erros Melhorado

## 🎯 O que Mudou?

**Antes**: Ao cometer erro em formulário → redirect + toast message  
**Depois**: Ao cometer erro em formulário → renderiza página novamente + mensagem + dados preenchidos

---

## 🧪 Teste #1: `create_die_work` (Criar Trabalho para Fieira)

**Arquivo**: theme/views.py, linha ~1670  
**Mudança**: Redirect → Render com contexto

### Teste Passo a Passo:

1. Vá para uma fieira (por exemplo, em "Listar Fieiras")
2. Clique em "Criar Trabalho"
3. **❌ Teste 1**: Deixe "Tipo de Trabalho" vazio, clique Submit
   - ✅ **Esperado**: Página não redireciona, mostra erro em toast TOP-DIREITO, form mantém-se visível
   - ✅ **Benefício**: Usuário vê exatamente onde errou

4. **❌ Teste 2**: Deixe "Subtipo" vazio, clique Submit
   - ✅ **Esperado**: Mesmo comportamento

5. **✅ Teste 3**: Preencha tudo, clique Submit
   - ✅ **Esperado**: Sucesso, redireciona para detalhes da fieira

---

## 🧪 Teste #2: `add_multiple_works_workers` (Adicionar Trabalho a Múltiplas Fieiras)

**Arquivo**: theme/views.py, linha ~1710  
**Mudança**: Redirect → Render + validações individuais + try/except

### Teste Passo a Passo:

1. Vá para um QR Code / Caixa
2. Clique em "Adicionar Trabalho a Múltiplas Fieiras"
3. **❌ Teste 1**: Deixe tudo vazio, clique Submit
   - ✅ **Esperado**: 4 mensagens de erro individuais (uma para cada campo)
   - ✅ **Esperado**: Página não redireciona, form visível
   - ✅ **Novo**: Antes tinha 1 mensagem genérica, agora tem 4 específicas!

4. **❌ Teste 2**: Selecione só fieiras, deixe "Trabalho" vazio
   - ✅ **Esperado**: Erro só para "Trabalho"
   - ✅ **Esperado**: Checkboxes de fieiras mantêm-se selecionados

5. **✅ Teste 3**: Preencha tudo corretamente
   - ✅ **Esperado**: Sucesso, trabalhos criados
   - ✅ **Novo**: Agora com try/except para erros inesperados

---

## 🧪 Teste #3: `observacoes_caixa` (Adicionar Observações)

**Arquivo**: theme/views.py, linha ~3260  
**Mudança**: Adicionada validação + try/except

### Teste Passo a Passo:

1. Vá para um QR Code / Caixa
2. Clique em "Adicionar Observações"
3. **❌ Teste 1**: Deixe a observação vazia, clique Submit
   - ✅ **Esperado NOVO**: Erro "A observação não pode estar vazia"
   - ✅ **Esperado NOVO**: Página não redireciona, form visível
   - ❌ **Antes**: Redirectava sem nada acontecer

4. **✅ Teste 2**: Escreva uma observação, clique Submit
   - ✅ **Esperado**: Sucesso, redireciona para lista
   - ✅ **Novo**: Log de auditoria registado

---

## 📋 Checklist de Testes

### ✅ Comportamento esperado em TODOS os testes acima:

- [ ] **Validação**: Erros são mostrados como toast (top-right)
- [ ] **Persistência**: Dados digitados aparecem novamente no form
- [ ] **UI**: A página NÃO redireciona quando há erro
- [ ] **Contexto**: Formulário permanece visível para corrigir
- [ ] **Sucesso**: Redireciona apenas quando tudo está correto
- [ ] **Logs**: Ações são registadas na tabela `globalLogs`

---

## 🔍 Como Verificar se Funciona

### No Navegador:
1. Abra DevTools (F12)
2. Vá para "Network" e "Console"
3. Envie o formulário
4. Verifique se há `302` (redirect) ou `200` (render na mesma página)
   - ❌ Erro: vê `302` redirect
   - ✅ Correto: vê `200` (renderiza na mesma página)

### Na Base de Dados:
```sql
-- Verificar se logs foram criados
SELECT * FROM theme_globallogs 
WHERE action LIKE '%trabalho%' OR action LIKE '%observação%'
ORDER BY created_at DESC LIMIT 5;
```

---

## 🎯 Próximos Passos

Após testar estas 3 views, aplicar o **mesmo padrão** para as outras 4 problemáticas:

1. ❌ `create_die_work` → ✅ **FEITO**
2. ❌ `add_multiple_works_workers` → ✅ **FEITO**
3. ❌ `observacoes_caixa` → ✅ **FEITO**
4. ⏳ `create_caixa` (criar QRData) - Linha ~1548
5. ⏳ `add_worker_to_die_work` - Linha ~1800
6. ⏳ `listar_calibracoes` - Linha ~2636
7. ⏳ `editar_pedido_inline` - Linha ~1775

---

## 🚀 Resultado Final

Após aplicar em todas as 7 views:
- **65% das views** → **100% das views** com tratamento correto
- Usuários **nunca mais verão páginas de erro** para validações
- **Mensagens de erro claras** no contexto do formulário
- **Dados não perdidos** quando há erro de validação

---

## 💡 Dica: Template

Se o seu template não tiver `value="{{ form_data.campo }}"`, adicione:

```html
<!-- Antes -->
<input type="text" name="tipo_trabalho" class="...">

<!-- Depois -->
<input type="text" name="tipo_trabalho" 
       value="{{ form_data.tipo_trabalho }}"
       class="...">
```

Assim os dados preenchidos aparecem novamente após erro!
