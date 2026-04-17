Para que o agente de codificação consiga realizar uma "cirurgia" precisa no seu código atual sem quebrar o que já funciona, criei o **`cloner_bridge_analysis.md`**.

Este documento serve como um mapa de engenharia reversa. Ele força a IA a olhar para o seu CLI não apenas como um script de download, mas como um **provedor de dados** para o novo `AgenteDataClear`.

---

# 📄 cloner_bridge_analysis.md

## 1. Objetivo da Análise

Mapear a infraestrutura atual do **Cloner CLI** para identificar pontos de acoplamento com o **AgenteDataClear**. O foco é transformar o output de "Exibição Web" (HTML/CSS/JS) em "Input de Dados" (Markdown/JSONL).

---

## 2. Auditoria de Arquitetura Atual

_O agente de codificação deve preencher/validar os seguintes pontos antes de iniciar a implementação:_

### A. Estrutura de Diretórios (Workdir)

- **Padrão atual:** Como os sites clonados são organizados? (Ex: `/clones/domain_com/assets/`).
- **Brecha de Adaptabilidade:** O `AgenteDataClear` precisará de um diretório de saída espelhado ou um arquivo único de dataset na raiz do projeto?

### B. Ciclo de Vida do Processo (Hooks)

- **Ponto de Injeção:** Onde termina a escrita do último arquivo HTML?
- **Necessidade:** Implementar um `Observer Pattern` ou um `Post-Process Hook` para disparar a limpeza de dados assim que a clonagem terminar.

---

## 3. Identificação de Brechas Técnicas

| Componente Atual           | Comportamento do Cloner                | Requisito DataClear                         | Brecha/Risco                                    |
| :------------------------- | :------------------------------------- | :------------------------------------------ | :---------------------------------------------- |
| **Parser de HTML**         | Focado em corrigir caminhos de assets. | Focado em extração semântica e limpeza.     | Conflito de concorrência na leitura do arquivo. |
| **Gerenciamento de State** | Salva logs de download.                | Deve salvar telemetria de tokens e limpeza. | Sobrecarga no log atual.                        |
| **Tratamento de JS**       | Baixa arquivos `.js` para execução.    | Deve ignorar e remover referências.         | Injeção de código indesejado no dataset.        |

---

## 4. Matriz de Adaptabilidade (To-Do para a IA)

O agente deve implementar as seguintes pontes (bridges) no código base:

### 1. The Output Switcher

Modificar o core para aceitar uma flag `--mode`:

- `--mode web`: Comportamento padrão (clonagem para web service).
- `--mode data`: Ativa o `AgenteDataClear` e suprime o download de imagens/fontes/scripts pesados (economia de banda e tempo).

### 2. Stream vs Batch Processing

- **Brecha:** Se o site for gigante, carregar todos os HTMLs em memória vai causar `MemoryOverflow`.
- **Solução:** O agente deve implementar um gerador Python que processe arquivo por arquivo, salvando em _append mode_ no JSONL final.

### 3. Metadata Mapping

O Cloner CLI já sabe a URL de origem. Essa informação deve ser passada via objeto para o `AgenteDataClear` para garantir a rastreabilidade (Source Attribution) exigida no mercado europeu.

---

## 5. Instrução de Prompt para o Agente de Codificação

> "Analise o código fonte do meu Cloner CLI utilizando os parâmetros do `cloner_bridge_analysis.md`. Identifique a função de encerramento de download e crie um ponto de extensão para o `AgenteDataClear`. Garanta que a extração de dados não corrompa os arquivos HTML originais. Proponha uma refatoração que permita o modo de extração de dados sem o download de ativos binários (JPG, PNG, WOFF) quando a flag `--data-only` estiver ativa."

---

### Por que isso é "Engenharia Pesada"?

Ao entregar esse MD para o Gemini, você não está pedindo "faça um script". Você está definindo:

1.  **Modo de operação** (Web vs Data).
2.  **Gerenciamento de recursos** (não baixar lixo se o objetivo é apenas dados).
3.  **Segurança de memória** (processamento via stream).

Isso garante que o seu **Antigravity** seja robusto o suficiente para rodar em servidores Linux na Europa processando milhares de páginas por minuto. Pronto para rodar o diagnóstico no seu código?
