# Tutorial: Como Habilitar o Docker Desktop no WSL

## Pré-requisitos

Antes de começar, certifique-se de que você tem:
- Windows 10 versão 2004 ou superior (Build 19041+) ou Windows 11
- WSL 2 instalado e configurado
- Privilégios de administrador no Windows

## Passo 1: Verificar e Instalar o WSL 2

Abra o PowerShell como administrador e execute:

```powershell
wsl --list --verbose
```

Se o WSL não estiver instalado, instale com:

```powershell
wsl --install
```

Para atualizar para WSL 2 (se necessário):

```powershell
wsl --set-default-version 2
```

## Passo 2: Instalar uma Distribuição Linux

Se você ainda não tem uma distribuição Linux instalada:

```powershell
wsl --install -d Ubuntu
```

Ou instale via Microsoft Store:
- Ubuntu
- Debian
- openSUSE
- Outras distribuições disponíveis

## Passo 3: Baixar e Instalar o Docker Desktop

1. Acesse o site oficial do Docker: https://www.docker.com/products/docker-desktop/
2. Baixe o Docker Desktop para Windows
3. Execute o instalador como administrador
4. Durante a instalação, certifique-se de que a opção **"Use WSL 2 instead of Hyper-V"** esteja marcada

## Passo 4: Configurar o Docker Desktop para WSL 2

Após a instalação:

1. **Inicie o Docker Desktop**
2. **Acesse as configurações**: Clique no ícone do Docker na bandeja do sistema → Settings
3. **Vá para Resources → WSL Integration**
4. **Habilite a integração**:
   - Marque "Enable integration with my default WSL distro"
   - Marque as distribuições específicas onde você quer usar o Docker
5. **Clique em "Apply & Restart"**

## Passo 5: Verificar a Instalação

Abra o terminal da sua distribuição WSL e execute:

```bash
docker --version
```

```bash
docker-compose --version
```

Teste se o Docker está funcionando:

```bash
docker run hello-world
```

## Configurações Adicionais (Opcionais)

### Alocar Recursos para WSL 2

Crie um arquivo `.wslconfig` em `C:\Users\<seu-usuario>\`:

```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```

### Configurar Docker para Usar menos Recursos

No Docker Desktop, vá em Settings → Resources e ajuste:
- Memory: 2-4GB (dependendo da sua RAM)
- CPU: 2-4 cores
- Disk image size: conforme necessário

## Comandos Úteis

### Gerenciar WSL
```powershell
# Listar distribuições
wsl --list --verbose

# Parar WSL
wsl --shutdown

# Reiniciar uma distribuição específica
wsl --terminate <nome-da-distro>
```

### Verificar Status do Docker
```bash
# Status dos containers
docker ps

# Status do serviço Docker
sudo service docker status

# Iniciar Docker (se necessário)
sudo service docker start
```

## Solução de Problemas Comuns

### Docker não inicia no WSL
1. Reinicie o Docker Desktop
2. Execute `wsl --shutdown` e reinicie a distribuição
3. Verifique se a virtualização está habilitada no BIOS

### "docker: command not found"
1. Verifique se a integração WSL está habilitada no Docker Desktop
2. Reinicie o terminal WSL
3. Reinstale o Docker Desktop se necessário

### Performance lenta
1. Mantenha os arquivos do projeto dentro do sistema de arquivos WSL (`/home/usuario/`)
2. Evite acessar arquivos do Windows (`/mnt/c/`) frequentemente
3. Ajuste os recursos alocados para WSL 2

## Vantagens do Docker no WSL 2

- **Performance superior** comparado ao WSL 1
- **Compatibilidade completa** com comandos Linux
- **Integração nativa** com o sistema de arquivos Linux
- **Menor consumo de recursos** comparado ao Hyper-V
- **Inicialização mais rápida** dos containers

## Conclusão

Com essas configurações, você terá o Docker Desktop funcionando perfeitamente no WSL 2, proporcionando uma experiência de desenvolvimento mais próxima ao ambiente Linux nativo, mas com a conveniência do Windows como sistema operacional principal.