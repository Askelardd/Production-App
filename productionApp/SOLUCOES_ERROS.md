# 🔧 Soluções: Melhorar Tratamento de Erros nas Views

## Problema
Quando utilizadores cometem erros (campos vazios, dados inválidos), a página redireciona para outra e mostra a mensagem como "toast". Idealmente, o formulário deveria ser **renderizado novamente** para que o utilizador veja os erros no contexto.

## ✅ Padrão Correto

```python
if request.method == 'POST':
    # 1. Validar dados
    if not campo:
        messages.error(request, "Campo é obrigatório")
        # 2. Renderizar novamente (NÃO redirect!)
        return render(request, 'template.html', {
            'context_data': values,
            'form_data': request.POST  # Manter dados do form
        })
    
    try:
        # 3. Processar
        obj.save()
        messages.success(request, "Sucesso!")
        return redirect('next_view')  # Redirecionar apenas no sucesso
    except Exception as e:
        messages.error(request, f"Erro: {str(e)}")
        # Renderizar novamente com dados
        return render(request, 'template.html', {
            'context_data': values,
            'form_data': request.POST
        })
```

---

## 🛠️ Solução #1: `create_die_work` (Linha 1670)

### ❌ Código Atual
```python
if not tipo_trabalho:
    messages.error(request, "Escolha um tipo de trabalho.")
    return redirect(request.path)  # ❌ Perde contexto
```

### ✅ Código Corrigido
```python
if not tipo_trabalho:
    messages.error(request, "Escolha um tipo de trabalho.")
    return render(request, 'theme/create_die_work.html', {
        'die': die,
        'tipo_trabalho': tipo_trabalho,  # Mantém dados
        'subtipo': subtipo
    })
if not subtipo:
    messages.error(request, "Escolha um subtipo.")
    return render(request, 'theme/create_die_work.html', {
        'die': die,
        'tipo_trabalho': tipo_trabalho,
        'subtipo': subtipo
    })
```

---

## 🛠️ Solução #2: `add_multiple_works_workers` (Linha 1710)

### ❌ Código Atual
```python
if not die_ids or not work_type or not subtype or not worker_ids:
    messages.error(request, "Todos os campos são obrigatórios.")
    return redirect(request.path)  # ❌ Usuário perde tudo que digitou

selected_workers = list(users.filter(id__in=worker_ids))
if len(selected_workers) != len(set(worker_ids)):
    messages.error(request, "Só é permitido selecionar...")
    return redirect(request.path)  # ❌ Perde contexto
```

### ✅ Código Corrigido
```python
# Validações com render
errors = []
if not die_ids:
    errors.append("Selecione pelo menos uma fieira.")
if not work_type:
    errors.append("Escolha um tipo de trabalho.")
if not subtype:
    errors.append("Escolha um subtipo.")
if not worker_ids:
    errors.append("Selecione pelo menos um trabalhador.")

if errors:
    for error in errors:
        messages.error(request, error)
    
    # Renderizar com dados preenchidos
    return render(request, 'theme/add_multiple_works_workers.html', {
        'qr_id': qr_id,
        'dies': dies,
        'users': users,
        'pedido': pedido,
        'form_data': {
            'die_ids': die_ids,
            'work_type': work_type,
            'subtype': subtype,
            'worker_ids': worker_ids
        }
    })

# Validação de segurança
selected_workers = list(users.filter(id__in=worker_ids))
if len(selected_workers) != len(set(worker_ids)):
    messages.error(request, "Só é permitido selecionar trabalhadores do grupo Producao.")
    return render(request, 'theme/add_multiple_works_workers.html', {
        'qr_id': qr_id,
        'dies': dies,
        'users': users,
        'pedido': pedido,
        'form_data': request.POST.dict()
    })

# Agora temos certeza que dados estão válidos
try:
    for die_id in die_ids:
        die = get_object_or_404(dieInstance, id=die_id)
        new_work = DieWork.objects.create(
            die=die, work_type=work_type, subtype=subtype
        )
        for user in selected_workers:
            DieWorkWorker.objects.create(
                work=new_work, worker=user, diam_min=0.0000, diam_max=0.0000
            )
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user.username} criou um trabalho '{work_type}' para o Die {die.serial_number} com {user.username}."
            )
    
    messages.success(request, f"{len(die_ids)} trabalho(s) adicionados com sucesso!")
    
    if add_another:
        return redirect('add_multiple_works_workers', qr_id=qr_id)
    return redirect('die_details', die_id=die_ids[-1])

except Exception as e:
    messages.error(request, f"Erro ao criar trabalhos: {str(e)}")
    return render(request, 'theme/add_multiple_works_workers.html', {
        'qr_id': qr_id,
        'dies': dies,
        'users': users,
        'pedido': pedido,
        'form_data': request.POST.dict()
    })
```

---

## 🛠️ Solução #3: `observacoes_caixa` (Linha 3234)

### ❌ Código Atual
```python
if nova_observacao:
    qr.observations_prod += f"\n\n{nova_observacao}"
    qr.save()
    messages.success(request, "Observações...")
    
return redirect('listarDies')  # ❌ Redireciona sempre, mesmo se vazio
```

### ✅ Código Corrigido
```python
if request.method == 'POST':
    nova_observacao = request.POST.get('nova_observacao', '').strip()
    
    if not nova_observacao:
        messages.error(request, "A observação não pode estar vazia.")
        return render(request, 'theme/observacoes_caixa.html', {
            'qr': qr,
            'qr_id': qr.id
        })
    
    try:
        # Se já existir texto antigo, juntamos o novo na linha de baixo
        if qr.observations_prod:
            qr.observations_prod += f"\n\n{nova_observacao}"
        else:
            qr.observations_prod = nova_observacao
        
        qr.save()
        
        # Log
        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} adicionou observação à caixa {qr.toma_order_full}."
        )
        
        messages.success(request, "Observações de produção atualizadas com sucesso!")
        return redirect('listarDies')
    
    except Exception as e:
        messages.error(request, f"Erro ao guardar observações: {str(e)}")
        return render(request, 'theme/observacoes_caixa.html', {
            'qr': qr,
            'qr_id': qr.id
        })

return render(request, 'theme/observacoes_caixa.html', {
    'qr': qr,
    'qr_id': qr.id
})
```

---

## 📊 Resumo das Mudanças

| Vista | Mudança | Benefício |
|------|---------|-----------|
| `create_die_work` | Render ao invés de redirect | Usuário vê erro no form |
| `add_multiple_works_workers` | Validações + render + try/except | Mantém dados, melhor feedback |
| `observacoes_caixa` | Validação vazia + try/except | Previne observações em branco |

---

## 🎯 Próximas Etapas

1. **Aplicar essas 3 soluções** no `views.py`
2. **Testar** cada uma:
   - Deixar campo vazio → deve ver erro
   - Digitar dados e submit → deve funcionar
3. **Replicar padrão** nas outras 4 views problemáticas

## 📝 Template: Mostrar Dados no Form (HTML)

No template, adicione um `value=` para manter dados já digitados:

```html
<input type="text" name="tipo_trabalho" 
       value="{{ form_data.tipo_trabalho }}"
       class="...">
```

Assim, se houver erro de validação, o usuário vê os dados que digitou, só precisa corrigir.
