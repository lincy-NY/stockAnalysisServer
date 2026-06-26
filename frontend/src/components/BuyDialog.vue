<template>
  <el-dialog
    v-model="visible"
    title="买入股票"
    width="500px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="股票代码" prop="ts_code">
        <el-input v-model="form.ts_code" disabled />
      </el-form-item>
      
      <el-form-item label="股票名称" prop="stock_name">
        <el-input v-model="form.stock_name" disabled />
      </el-form-item>
      
      <el-form-item label="选股日期" prop="screen_date">
        <el-input v-model="form.screen_date" disabled />
      </el-form-item>
      
      <el-form-item label="当前价格" prop="current_price">
        <el-input v-model="form.current_price" disabled>
          <template #append>元</template>
        </el-input>
      </el-form-item>
      
      <el-divider />
      
      <el-form-item label="购买日期" prop="buy_date">
        <el-date-picker
          v-model="form.buy_date"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      
      <el-form-item label="购买数量" prop="buy_amount">
        <el-input-number
          v-model="form.buy_amount"
          :min="100"
          :step="100"
          style="width: 100%"
        >
          <template #append>股</template>
        </el-input-number>
      </el-form-item>
      
      <el-form-item label="购买均价" prop="buy_price">
        <el-input-number
          v-model="form.buy_price"
          :min="0.01"
          :precision="2"
          style="width: 100%"
        >
          <template #append>元</template>
        </el-input-number>
      </el-form-item>
      
      <el-form-item label="总金额">
        <el-input v-model="totalAmount" disabled>
          <template #append>元</template>
        </el-input>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">确认买入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { buyStock } from '@/utils/api'

const emit = defineEmits(['success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = ref({
  ts_code: '',
  stock_name: '',
  screen_date: '',
  current_price: 0,
  buy_date: new Date().toISOString().split('T')[0],
  buy_amount: 100,
  buy_price: 0
})

const rules = {
  buy_date: [{ required: true, message: '请选择购买日期', trigger: 'change' }],
  buy_amount: [
    { required: true, message: '请输入购买数量', trigger: 'blur' },
    { type: 'number', message: '必须为数字', trigger: 'blur' }
  ],
  buy_price: [
    { required: true, message: '请输入购买均价', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '必须大于0', trigger: 'blur' }
  ]
}

const totalAmount = computed(() => {
  return (form.value.buy_amount * form.value.buy_price).toFixed(2)
})

const open = (data) => {
  form.value = {
    ts_code: data.ts_code,
    stock_name: data.stock_name,
    screen_date: data.screen_date,
    current_price: data.close,
    buy_date: new Date().toISOString().split('T')[0],
    buy_amount: 100,
    buy_price: data.close
  }
  visible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    
    loading.value = true
    await buyStock({
      ts_code: form.value.ts_code,
      screen_date: form.value.screen_date,
      buy_date: form.value.buy_date,
      buy_price: form.value.buy_price,
      buy_amount: form.value.buy_amount
    })
    
    ElMessage.success('买入成功')
    visible.value = false
    emit('success')
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.detail || '买入失败')
    }
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  formRef.value?.resetFields()
}

defineExpose({ open })
</script>

<style scoped>
.el-divider {
  margin: 10px 0;
}
</style>