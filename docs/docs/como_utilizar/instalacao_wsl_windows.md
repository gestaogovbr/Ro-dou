# Guia de Instalação e Configuração do WSL no Windows

## Índice
- [Pré-requisitos](#pré-requisitos)
- [Instalação do WSL](#instalação-do-wsl)
- [Configuração Inicial](#configuração-inicial)
- [Configurações Avançadas](#configurações-avançadas)
- [Comandos Úteis](#comandos-úteis)
- [Solução de Problemas](#solução-de-problemas)

## Pré-requisitos

### Versões do Windows Compatíveis
- Windows 10 versão 2004 ou superior (Build 19041 ou superior)
- Windows 11 (todas as versões)

### Verificar Versão do Windows
1. Pressione `Win + R`
2. Digite `winver` e pressione Enter
3. Verifique se sua versão atende aos requisitos

### Habilitar Recursos Necessários
Antes da instalação, alguns recursos do Windows devem estar habilitados:

1. **Abra o PowerShell como Administrador**
   - Clique com botão direito no menu Iniciar
   - Selecione "Windows PowerShell (Admin)" ou "Terminal (Admin)"

2. **Execute os seguintes comandos:**
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

3. **Reinicie o computador**

## Instalação do WSL

### Método 1: Instalação Automática (Recomendado)

**Para Windows 10 versão 2004+ e Windows 11:**

1. **Abra o PowerShell ou Terminal como Administrador**

2. **Execute o comando de instalação:**
```powershell
wsl --install
```

3. **Reinicie o computador quando solicitado**

4. **Após a reinicialização, o Ubuntu será instalado automaticamente**

### Método 2: Instalação Manual

Se o método automático não funcionar:

1. **Baixe e instale o pacote de atualização do kernel do Linux:**
   - Acesse: https://aka.ms/wsl2kernel
   - Baixe e instale o arquivo MSI

2. **Defina WSL 2 como versão padrão:**
```powershell
wsl --set-default-version 2
```

3. **Instale uma distribuição Linux:**
   - Acesse a Microsoft Store
   - Pesquise por "Ubuntu", "Debian", "openSUSE", etc.
   - Clique em "Instalar"

## Configuração Inicial

### Primeira Configuração da Distribuição

1. **Abra a distribuição Linux instalada**
   - Procure no menu Iniciar (ex: "Ubuntu")
   - Ou digite `wsl` no Terminal/PowerShell

2. **Configure usuário e senha:**
   - Digite um nome de usuário (minúsculas, sem espaços)
   - Digite uma senha (não será exibida durante a digitação)
   - Confirme a senha

### Atualizar o Sistema

Após a configuração inicial:

```bash
sudo apt update && sudo apt upgrade -y
```

### Verificar Instalação

Para verificar se o WSL está funcionando corretamente:

```powershell
wsl --list --verbose
```

## Configurações Avançadas

### Arquivo .wslconfig

Crie um arquivo `.wslconfig` na pasta do usuário Windows (`C:\Users\SeuUsuario\.wslconfig`):

```ini
[wsl2]
# Limitar memória RAM (exemplo: 4GB)
memory=4GB

# Limitar número de processadores
processors=2

# Habilitar swap
swap=2GB

# Desabilitar página de memória virtual
pageReporting=false

# Especificar kernel customizado (opcional)
# kernel=C:\\temp\\myCustomKernel

# Argumentos adicionais do kernel
# kernelCommandLine = vsyscall=emulate

# Habilitar conexões localhost
localhostForwarding=true

# Habilitar modo debug
# debugConsole=true
```

### Configurações por Distribuição

Crie um arquivo `wsl.conf` dentro da distribuição Linux (`/etc/wsl.conf`):

```ini
[automount]
enabled = true
root = /mnt/
options = "metadata,umask=22,fmask=11"
mountFsTab = false

[network]
generateHosts = true
generateResolvConf = true
hostname = meu-wsl

[interop]
enabled = true
appendWindowsPath = true

[user]
default = seu-usuario

[boot]
systemd = true
```

### Configurar Git (Recomendado)

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu.email@exemplo.com"
```

### Instalar Ferramentas Essenciais

```bash
# Ferramentas básicas de desenvolvimento
sudo apt install curl wget git vim nano build-essential

# Node.js e npm
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python e pip
sudo apt install python3 python3-pip

# Docker (se necessário)
sudo apt install docker.io
sudo usermod -aG docker $USER
```

## Comandos Úteis

### Comandos Básicos do WSL

```powershell
# Listar distribuições instaladas
wsl --list --verbose

# Listar distribuições disponíveis para download
wsl --list --online

# Instalar uma distribuição específica
wsl --install -d Ubuntu-22.04

# Definir distribuição padrão
wsl --set-default Ubuntu-22.04

# Iniciar uma distribuição específica
wsl -d Ubuntu-22.04

# Parar uma distribuição
wsl --terminate Ubuntu-22.04

# Parar todas as distribuições
wsl --shutdown

# Fazer backup de uma distribuição
wsl --export Ubuntu-22.04 C:\backup\ubuntu-backup.tar

# Restaurar uma distribuição
wsl --import Ubuntu-Restaurada C:\WSL\Ubuntu-Restaurada C:\backup\ubuntu-backup.tar

# Desinstalar uma distribuição
wsl --unregister Ubuntu-22.04

# Verificar versão do WSL
wsl --version

# Atualizar WSL
wsl --update
```

### Acessar Arquivos

**Do Windows para Linux:**
```
\\wsl$\Ubuntu-22.04\home\usuario
```

**Do Linux para Windows:**
```bash
cd /mnt/c/Users/SeuUsuario
```

### Executar Comandos

**Executar comando Linux do Windows:**
```powershell
wsl ls -la
wsl -d Ubuntu-22.04 ls -la
```

**Executar comando Windows do Linux:**
```bash
cmd.exe /c dir
powershell.exe -c "Get-Process"
```

## Solução de Problemas

### Erro: "WslRegisterDistribution failed with error: 0x80073712"

**Solução:**
1. Habilite o recurso "Plataforma de Máquina Virtual":
```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```
2. Reinicie o computador

### Erro: "WslRegisterDistribution failed with error: 0x8007019e"

**Solução:**
1. Habilite o WSL:
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```
2. Reinicie o computador

### WSL 2 requer uma atualização

**Solução:**
1. Baixe o pacote de atualização: https://aka.ms/wsl2kernel
2. Execute o arquivo baixado
3. Defina WSL 2 como padrão:
```powershell
wsl --set-default-version 2
```

### Performance lenta

**Soluções:**
1. Certifique-se de que está usando WSL 2:
```powershell
wsl --set-version Ubuntu-22.04 2
```

2. Mantenha arquivos no sistema de arquivos Linux para melhor performance

3. Configure limites de recursos no arquivo `.wslconfig`

### Problemas de conectividade de rede

**Solução:**
1. Reinicie o WSL:
```powershell
wsl --shutdown
```

2. Desabilite o firewall temporariamente para teste

3. Configure DNS manualmente em `/etc/resolv.conf`:
```bash
nameserver 8.8.8.8
nameserver 8.8.4.4
```

### Não consegue acessar arquivos Windows

**Solução:**
1. Verifique se a montagem automática está habilitada em `/etc/wsl.conf`
2. Reinicie o WSL após alterações de configuração

## Dicas Extras

### Integração com VS Code

1. Instale a extensão "Remote - WSL" no VS Code
2. Abra um projeto WSL: `code .` dentro da pasta do projeto no Linux
3. Ou use `Ctrl+Shift+P` > "Remote-WSL: New Window"

### Usar Windows Terminal

1. Instale o Windows Terminal da Microsoft Store
2. Ele detectará automaticamente suas distribuições WSL
3. Configure perfis personalizados para cada distribuição

### Backup Automático

Crie um script PowerShell para backup regular:

```powershell
# backup-wsl.ps1
$data = Get-Date -Format "yyyy-MM-dd"
wsl --export Ubuntu-22.04 "C:\Backups\Ubuntu-$data.tar"
```

---

**Nota:** Sempre execute comandos PowerShell como Administrador quando necessário e mantenha o WSL atualizado com `wsl --update`.