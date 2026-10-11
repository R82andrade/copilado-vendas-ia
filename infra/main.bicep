@description('Localização do recurso Azure')
param location string = resourceGroup().location

@description('Nome da aplicação')
param appName string = 'vendas-api-demo'

@description('SKU do plano')
param skuName string = 'B1'

@description('Tamanho do plano')
param skuCapacity int = 1

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

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
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
      ]
    }
  }
}

output appUrl string = 'https://${webApp.properties.defaultHostName}'
