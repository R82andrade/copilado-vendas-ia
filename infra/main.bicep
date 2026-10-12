@description('Localização do recurso Azure')
param location string = resourceGroup().location

@description('Nome da aplicação')
param appName string = 'vendas-api-demo'

@description('SKU do plano')
param skuName string = 'B1'

@description('Tamanho do plano')
param skuCapacity int = 1

@description('Nome do banco de dados PostgreSQL')
param databaseName string = 'vendas'

@description('Usuário administrador inicial do PostgreSQL. Use apenas letras e números.')
param databaseAdminUsername string = 'vendasadmin'

@secure()
@minLength(16)
@maxLength(32)
@description('Senha do banco: use apenas letras e números para manter a URL de conexão válida.')
param databaseAdminPassword string

@secure()
@minLength(32)
@description('Segredo de assinatura dos tokens. Gere um valor aleatório com pelo menos 32 caracteres.')
param authSecret string

@description('Usuário inicial administrador do painel')
param adminUsername string = 'admin'

@secure()
@minLength(12)
@description('Senha inicial do administrador do painel')
param adminPassword string

@description('SKU do servidor PostgreSQL')
param postgresSku string = 'Standard_B1ms'

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${appName}-plan'
  location: location
  kind: 'linux'
  sku: {
    name: skuName
    tier: 'Basic'
    capacity: skuCapacity
  }
  properties: {
    reserved: true
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${appName}-db'
  location: location
  sku: {
    name: postgresSku
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: databaseAdminUsername
    administratorLoginPassword: databaseAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgres
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource azureServicesFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'AUTH_REQUIRED'
          value: 'true'
        }
        {
          name: 'AUTH_SECRET'
          value: authSecret
        }
        {
          name: 'ADMIN_USERNAME'
          value: adminUsername
        }
        {
          name: 'ADMIN_PASSWORD'
          value: adminPassword
        }
        {
          name: 'DATABASE_URL'
          value: 'postgresql+psycopg2://${databaseAdminUsername}:${databaseAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'
        }
        {
          name: 'FRONTEND_ORIGINS'
          value: 'https://${appName}.azurewebsites.net'
        }
      ]
    }
  }
  dependsOn: [postgresDatabase, azureServicesFirewall]
}

output appUrl string = 'https://${webApp.properties.defaultHostName}'
